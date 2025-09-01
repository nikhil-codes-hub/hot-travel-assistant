from pydantic import BaseModel
from typing import Dict, List, Any, Optional

class AgentResponse(BaseModel):
    """Standard response format for all agents"""
    response: str
    suggestions: List[str] = []
    agent_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = {}
    session_id: Optional[str] = None