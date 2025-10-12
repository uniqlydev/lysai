from core.db_client import get_client

def main():
    conn, cur = get_client()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    print("Tables:")
    for row in tables:
        print("-", row[0])
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()