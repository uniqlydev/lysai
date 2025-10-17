from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class AgentState(BaseModel):
    """
    Represents the state of an agent, including its name, type, and additional attributes.
    """
    question: str
    plan: Optional[List[str]] = None
    sql: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    available_tools: Optional[List[Dict[str, Any]]] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    episode_id: Optional[int] = None

    # Agentic 
    step: int = 0
    max_steps: int = 6
    action: Optional[Dict[str, Any]] = None
    observation: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    

