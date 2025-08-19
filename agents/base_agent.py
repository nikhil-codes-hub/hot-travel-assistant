"""
Base Agent Class

All travel agents should inherit from this base class to ensure consistent
interface and behavior across the HOT Travel Assistant ecosystem.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Standard response format for all agents"""
    response: str
    suggestions: List[str] = []
    agent_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = {}


class BaseAgent(ABC):
    """
    Base class for all travel assistance agents.
    
    Each agent should specialize in a specific domain (visas, flights, hotels, etc.)
    and provide consistent interface for the LangGraph orchestrator.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.agent_type = self.__class__.__name__
    
    @abstractmethod
    async def can_handle(self, query: str) -> bool:
        """
        Determine if this agent can handle the given query.
        
        Args:
            query: User's input query
            
        Returns:
            bool: True if agent can handle this query
        """
        pass
    
    @abstractmethod
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process the user query and return a response.
        
        Args:
            query: User's input query
            context: Optional context from other agents or previous interactions
            
        Returns:
            AgentResponse: Structured response with suggestions
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Return list of capabilities this agent provides.
        
        Returns:
            List[str]: List of capability descriptions
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities()
        }