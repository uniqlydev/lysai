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

