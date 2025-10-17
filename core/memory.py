import os, json, sqlite3, datetime, dotenv
from typing import List, Dict, Any, Optional

dotenv.load_dotenv()


DB_PATH = os.getenv("MEMORY_DB", "memory_store/memory.db")

def init_database():
    """Initialize the database with required tables and FTS index"""
    with _conn() as conn:
        cursor = conn.cursor()
        
        # Create episodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                question TEXT,
                plan_json TEXT,
                sql TEXT,
                rows_json TEXT,
                outcome TEXT,
                error TEXT,
                insight TEXT
            )
        """)
        
        # Create FTS table for search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
                question, sql, insight,
                content='episodes',
                content_rowid='id'
            )
        """)
        
        # Create triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                INSERT INTO fts(rowid, question, sql, insight) 
                VALUES (NEW.id, NEW.question, NEW.sql, NEW.insight);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN
                UPDATE fts SET question=NEW.question, sql=NEW.sql, insight=NEW.insight 
                WHERE rowid=NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                DELETE FROM fts WHERE rowid=OLD.id;
            END
        """)
        
        conn.commit()

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn 

def log_episode(question: str, plan: Optional[List[str]] = None,
                sql: Optional[str] = None,
                rows: Optional[List[Dict[str, Any]]] = None, 
                outcome: Optional[str] = None,
                error: Optional[str] = None,
                insight: Optional[str] = None) -> int:
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Initialize database if needed
    init_database()

    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO episodes (timestamp, question, plan_json, sql, rows_json, outcome, error, insight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts,
            question,
            json.dumps(plan) if plan is not None else None,
            sql,
            json.dumps(rows or []),
            outcome,
            error,
            insight
        ))

        conn.commit()
        episode_id = int(cursor.lastrowid)

        try:
            from .semantic import get_semantic_memory
            if question or insight:
                semantic_memory = get_semantic_memory()
                semantic_memory.add_episode_to_semantic_memory(episode_id=episode_id, question=question, insight=insight)
        except Exception as e:
            print(f"Warning: Failed to add episode to semantic memory: {e}")

        return episode_id
    
def update_episode(ep_id: int, **fields):
    if not fields:
        return
    
    cols, vals = [], []

    for k, v in fields.items():
        if k == "plan": 
            k, v = "plan_json", json.dumps(v) if v is not None else None
        elif k == "rows": 
            k, v = "rows_json", json.dumps(v or [])
        cols.append(f"{k} = ?")
        vals.append(v)

    vals.append(ep_id)  # Add episode ID for WHERE clause
    
    with _conn() as c:
        c.execute("UPDATE episodes SET " + ", ".join(cols) + " WHERE id = ?", vals)
        c.commit()

        if 'insight' in fields and fields['insight']:
            try:
                from .semantic import get_semantic_memory
                episode = get_episode(episode_id=ep_id)

                if episode:
                    semantic = get_semantic_memory()
                    semantic.add_episode_to_semantic_memory(
                        episode_id=ep_id,
                        question=episode.get('question', ''),
                        fields=fields['insight']
                    )
            except Exception as e:
                print(f"Warning: Failed to update episode in semantic memory: {e}")

def search_similar(q: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for episodes similar to the given question"""
    init_database()
    
    with _conn() as c:
        try:
            rows = c.execute("""
                SELECT e.*, rank
                FROM fts JOIN episodes e ON fts.rowid = e.id
                WHERE fts MATCH ? 
                ORDER BY rank
                LIMIT ?""", (q, limit)).fetchall()
            
            results = []
            for row in rows:
                episode = dict(row)
                # Parse JSON fields back to objects
                if episode.get('plan_json'):
                    try:
                        episode['plan'] = json.loads(episode['plan_json'])
                    except:
                        episode['plan'] = None
                if episode.get('rows_json'):
                    try:
                        episode['rows'] = json.loads(episode['rows_json'])
                    except:
                        episode['rows'] = []
                results.append(episode)
            
            return results
        except sqlite3.OperationalError:
            # FTS table might not exist or be populated yet
            return []
    
def recent_successes(limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent successful episodes"""
    init_database()
    
    with _conn() as c:
        rows = c.execute("""
            SELECT * FROM episodes 
            WHERE outcome = 'success' AND sql IS NOT NULL
            ORDER BY id DESC 
            LIMIT ?""", (limit,)).fetchall()

        results = []
        for row in rows:
            episode = dict(row)
            # Parse JSON fields back to objects
            if episode.get('plan_json'):
                try:
                    episode['plan'] = json.loads(episode['plan_json'])
                except:
                    episode['plan'] = None
            if episode.get('rows_json'):
                try:
                    episode['rows'] = json.loads(episode['rows_json'])
                except:
                    episode['rows'] = []
            results.append(episode)

        return results

def get_episode(episode_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific episode by ID"""
    init_database()
    
    with _conn() as c:
        row = c.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
        
        if row:
            episode = dict(row)
            # Parse JSON fields back to objects
            if episode.get('plan_json'):
                try:
                    episode['plan'] = json.loads(episode['plan_json'])
                except:
                    episode['plan'] = None
            if episode.get('rows_json'):
                try:
                    episode['rows'] = json.loads(episode['rows_json'])
                except:
                    episode['rows'] = []
            return episode
        
        return None

# Alias for backwards compatibility
init = init_database
                         