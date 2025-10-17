import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .memory import get_episode, recent_successes, search_similar
import dotenv

dotenv.load_dotenv()

@dataclass
class SemanticMatch:
    """Represents a semantically similar memory item"""
    episode_id: int
    episode: Dict[str, Any]
    distance: float  # ChromaDB returns distance (lower = more similar)
    similarity: float  # Converted to similarity score (higher = more similar)
    content_type: str  # 'question' or 'insight'

class SemanticMemory:
    """
    Semantic memory using ChromaDB for vector storage and retrieval.
    Integrates with the existing SQLite episodic memory.
    """
    
    def __init__(self, persist_directory: Optional[str] = None):
        # Use environment variable or default path
        if persist_directory is None:
            persist_directory = os.getenv("CHROMA_DB_PATH", "memory_store/chroma_db")
        
        # Create ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collections
        self.questions_collection = self.client.get_or_create_collection(
            name="episode_questions",
            metadata={"description": "Questions from episodic memory"}
        )
        
        self.insights_collection = self.client.get_or_create_collection(
            name="episode_insights", 
            metadata={"description": "Insights and learnings from episodes"}
        )
    
    def add_episode_to_semantic_memory(self, episode_id: int, question: str, 
                                     insight: Optional[str] = None):
        """
        Add an episode's question and insight to semantic memory.
        Called when logging new episodes.
        """
        try:
            # Add question to questions collection
            if question:
                self.questions_collection.add(
                    documents=[question],
                    metadatas=[{
                        "episode_id": episode_id,
                        "content_type": "question",
                        "timestamp": str(episode_id)  # Using episode_id as rough timestamp
                    }],
                    ids=[f"question_{episode_id}"]
                )
            
            # Add insight to insights collection
            if insight:
                self.insights_collection.add(
                    documents=[insight],
                    metadatas=[{
                        "episode_id": episode_id,
                        "content_type": "insight", 
                        "timestamp": str(episode_id)
                    }],
                    ids=[f"insight_{episode_id}"]
                )
                
            print(f"Added episode {episode_id} to semantic memory")
            
        except Exception as e:
            print(f"Warning: Could not add episode {episode_id} to semantic memory: {e}")
    
    def search_similar_questions(self, query: str, limit: int = 5) -> List[SemanticMatch]:
        """Find episodes with similar questions"""
        try:
            results = self.questions_collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            matches = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0], 
                results['distances'][0]
            )):
                episode_id = metadata['episode_id']
                episode = get_episode(episode_id)
                
                if episode:
                    # Convert distance to similarity (0-1 scale, higher = more similar)
                    similarity = max(0, 1 - distance)
                    
                    matches.append(SemanticMatch(
                        episode_id=episode_id,
                        episode=episode,
                        distance=distance,
                        similarity=similarity,
                        content_type="question"
                    ))
            
            return matches
            
        except Exception as e:
            print(f"Warning: Could not search similar questions: {e}")
            return []
    
    def search_similar_insights(self, query: str, limit: int = 5) -> List[SemanticMatch]:
        """Find episodes with similar insights"""
        try:
            results = self.insights_collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            matches = []
            for doc, metadata, distance in zip(
                results['documents'][0], 
                results['metadatas'][0], 
                results['distances'][0]
            ):
                episode_id = metadata['episode_id']
                episode = get_episode(episode_id)
                
                if episode:
                    similarity = max(0, 1 - distance)
                    
                    matches.append(SemanticMatch(
                        episode_id=episode_id,
                        episode=episode,
                        distance=distance,
                        similarity=similarity,
                        content_type="insight"
                    ))
            
            return matches
            
        except Exception as e:
            print(f"Warning: Could not search similar insights: {e}")
            return []
    
    def search_all_semantic(self, query: str, limit: int = 5) -> List[SemanticMatch]:
        """Search both questions and insights, return best matches"""
        question_matches = self.search_similar_questions(query, limit)
        insight_matches = self.search_similar_insights(query, limit)
        
        # Combine and sort by similarity
        all_matches = question_matches + insight_matches
        all_matches.sort(key=lambda x: x.similarity, reverse=True)
        
        return all_matches[:limit]
    
    def find_similar_patterns(self, question: str, limit: int = 3) -> List[SemanticMatch]:
        """
        Find episodes with similar question patterns.
        Focus on successful episodes with SQL.
        """
        matches = self.search_similar_questions(question, limit * 2)
        
        # Filter to successful episodes with SQL
        successful_matches = [
            match for match in matches 
            if match.episode.get('outcome') == 'success' 
            and match.episode.get('sql')
            and match.similarity > 0.3  # Minimum similarity threshold
        ]
        
        return successful_matches[:limit]
    
    def find_relevant_insights(self, context: str, limit: int = 3) -> List[SemanticMatch]:
        """
        Find episodes with relevant insights for the given context.
        """
        matches = self.search_similar_insights(context, limit)
        
        # Filter to episodes with meaningful insights
        relevant_matches = [
            match for match in matches 
            if match.episode.get('insight')
            and match.similarity > 0.2  # Lower threshold for insights
        ]
        
        return relevant_matches[:limit]
    
    def get_learning_context(self, current_question: str) -> Dict[str, Any]:
        """
        Get comprehensive learning context for planning and execution.
        """
        similar_patterns = self.find_similar_patterns(current_question)
        relevant_insights = self.find_relevant_insights(current_question)
        
        return {
            'similar_patterns': [
                {
                    'episode_id': match.episode_id,
                    'question': match.episode['question'],
                    'sql': match.episode.get('sql'),
                    'similarity': match.similarity,
                    'outcome': match.episode.get('outcome')
                }
                for match in similar_patterns
            ],
            'relevant_insights': [
                {
                    'episode_id': match.episode_id,
                    'insight': match.episode['insight'],
                    'original_question': match.episode['question'],
                    'similarity': match.similarity
                }
                for match in relevant_insights
            ],
            'total_similar_patterns': len(similar_patterns),
            'total_insights': len(relevant_insights)
        }
    
    def populate_from_existing_episodes(self):
        """
        Populate semantic memory from existing episodes in SQLite.
        Useful for initial setup or rebuilding the semantic index.
        """
        print("Populating semantic memory from existing episodes...")
        
        # Get recent successful episodes to populate
        episodes = recent_successes(limit=100)  # Adjust limit as needed
        
        for episode in episodes:
            self.add_episode_to_semantic_memory(
                episode_id=episode['id'],
                question=episode.get('question'),
                insight=episode.get('insight')
            )
        
        print(f"Populated semantic memory with {len(episodes)} episodes")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the semantic memory collections"""
        return {
            'questions_count': self.questions_collection.count(),
            'insights_count': self.insights_collection.count(),
            'total_items': self.questions_collection.count() + self.insights_collection.count()
        }

# Singleton pattern for global access
_semantic_memory_instance = None

def get_semantic_memory() -> SemanticMemory:
    """Get singleton SemanticMemory instance"""
    global _semantic_memory_instance
    if _semantic_memory_instance is None:
        _semantic_memory_instance = SemanticMemory()
    return _semantic_memory_instance

def search_semantic(query: str, limit: int = 5) -> List[SemanticMatch]:
    """Quick access to semantic search across all content"""
    return get_semantic_memory().search_all_semantic(query, limit)

def get_learning_context(question: str) -> Dict[str, Any]:
    """Quick access to learning context for agents"""
    return get_semantic_memory().get_learning_context(question)

def populate_semantic_memory():
    """Helper to populate semantic memory from existing episodes"""
    get_semantic_memory().populate_from_existing_episodes()