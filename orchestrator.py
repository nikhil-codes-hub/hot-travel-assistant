"""
HOT Travel Assistant Orchestrator

Uses LangGraph to coordinate multiple travel agents and provide intelligent
routing and response orchestration for complex travel queries.
"""

import logging
from typing import Dict, List, Optional, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from typing_extensions import TypedDict

from agents import VisaAgent
from agents import HealthAgent
from agents.base_agent import AgentResponse

logger = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """State object for the conversation graph"""
    query: str
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]
    current_agent: Optional[str]
    response: Optional[AgentResponse]
    confidence: float


class TravelOrchestrator:
    """
    Main orchestrator for HOT Travel Assistant agents.
    
    Uses LangGraph to intelligently route queries to appropriate agents
    and coordinate multi-agent responses for complex travel planning.
    """
    
    def __init__(self):
        self.agents = {}
        self.graph = None
        self._initialize_agents()
        self._build_graph()
    
    def _initialize_agents(self):
        """Initialize all available travel agents"""
        try:
            # Core visa agent
            self.agents["visa"] = VisaAgent()
            self.agents["health"] = HealthAgent()
            logger.info("✅ Orchestrator: Visa agent initialized")
            
            # Placeholder for future agents that team members will add
            # self.agents["flight"] = FlightAgent()
            # self.agents["hotel"] = HotelAgent() 
            # self.agents["weather"] = WeatherAgent()
            # self.agents["currency"] = CurrencyAgent()
            
            logger.info(f"✅ Orchestrator: {len(self.agents)} agents available")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator: Failed to initialize agents: {e}")
    
    def _build_graph(self):
        """Build the LangGraph workflow for agent orchestration"""
        try:
            # Create the state graph
            workflow = StateGraph(ConversationState)
            
            # Add nodes
            workflow.add_node("route_query", self._route_query)
            workflow.add_node("process_visa", self._process_visa)
            workflow.add_node("process_health", self._process_health)
            workflow.add_node("fallback_response", self._fallback_response)
            
            # Add edges
            workflow.set_entry_point("route_query")
            
            # Conditional routing based on agent detection
            workflow.add_conditional_edges(
                "route_query",
                self._routing_decision,
                {
                    "visa": "process_visa",
                    "health": "process_health",
                    "fallback": "fallback_response"
                }
            )
            
            # End after processing
            workflow.add_edge("process_visa", END)
            workflow.add_edge("process_health", END)
            workflow.add_edge("fallback_response", END)
            
            # Compile the graph
            self.graph = workflow.compile()
            logger.info("✅ Orchestrator: LangGraph workflow compiled")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator: Failed to build graph: {e}")
            self.graph = None
    
    async def process_query(self, query: str, user_id: str = "anonymous") -> AgentResponse:
        """
        Process user query through the agent orchestration system.
        
        Args:
            query: User's travel query
            user_id: Optional user identifier for context
            
        Returns:
            AgentResponse: Orchestrated response from appropriate agent(s)
        """
        try:
            if not self.graph:
                # Fallback to direct agent routing if graph failed to initialize
                logger.warning("Orchestrator: Graph not available, using direct agent routing")
                visa_agent = self.agents.get("visa")
                health_agent = self.agents.get("health")
                if visa_agent and await visa_agent.can_handle(query):
                    return await visa_agent.process(query)
                elif health_agent and await health_agent.can_handle(query):
                    return await health_agent.process(query)
                else:
                    return self._create_fallback_response()
            
            # Graph is available - use LangGraph workflow
            logger.info("Orchestrator: Using LangGraph workflow")
            
            # Initialize conversation state
            initial_state: ConversationState = {
                "query": query,
                "messages": [],
                "context": {"user_id": user_id},
                "current_agent": None,
                "response": None,
                "confidence": 0.0
            }
            
            # Run the graph
            result = await self.graph.ainvoke(initial_state)
            
            # Return the response
            if result.get("response"):
                return result["response"]
            else:
                return self._create_fallback_response()
                
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return self._create_fallback_response()
    
    async def _route_query(self, state: ConversationState) -> ConversationState:
        """Analyze query and determine which agent should handle it"""
        query = state["query"]
        logger.info(f"Orchestrator: Routing query: {query}")
        
        # Calculate confidence scores for each agent
        agent_scores = {}
        for agent_name, agent in self.agents.items():
            try:
                if await agent.can_handle(query):
                    # Calculate specificity score based on keyword matches
                    score = self._calculate_agent_score(query, agent_name)
                    agent_scores[agent_name] = score
                    logger.info(f"Orchestrator: {agent_name} agent score: {score}")
            except Exception as e:
                logger.warning(f"Orchestrator: Error checking {agent_name} agent: {e}")
        
        if agent_scores:
            # Select agent with highest score
            best_agent = max(agent_scores, key=agent_scores.get)
            state["current_agent"] = best_agent
            state["confidence"] = min(agent_scores[best_agent] / 10.0, 0.9)
            logger.info(f"Orchestrator: Routed to {best_agent} agent (score: {agent_scores[best_agent]})")
            return state
        
        # No specific agent found, use fallback
        state["current_agent"] = "fallback" 
        state["confidence"] = 0.3
        logger.info("Orchestrator: Using fallback response")
        return state
    
    def _calculate_agent_score(self, query: str, agent_name: str) -> float:
        """Calculate specificity score for agent based on contextual analysis"""
        query_lower = query.lower()
        score = 0.0
        
        # Get agent instance to access its keyword methods
        agent = self.agents.get(agent_name)
        if not agent:
            return 0.0
        
        # Get agent-specific keywords and phrases
        keyword_weights = agent.get_keyword_weights()
        contextual_phrases = agent.get_contextual_phrases()
        penalty_keywords = agent.get_penalty_keywords()
        
        # Check for contextual phrases first (highest weight)
        for phrase in contextual_phrases:
            if phrase in query_lower:
                score += 10.0
        
        # Check primary keywords (high weight)
        for keyword in keyword_weights.get("primary", []):
            if keyword in query_lower:
                score += 5.0
        
        # Check secondary keywords (medium weight)
        for keyword in keyword_weights.get("secondary", []):
            if keyword in query_lower:
                score += 3.0
        
        # Check tertiary keywords (low weight)
        for keyword in keyword_weights.get("tertiary", []):
            if keyword in query_lower:
                score += 1.0
        
        # Handle overlapping keywords with context disambiguation
        overlapping_keywords = ["requirements", "documents", "need", "necessary", "brazil", "kenya", "thailand"]
        
        for keyword in overlapping_keywords:
            if keyword in query_lower:
                # Analyze surrounding context to determine relevance
                context_boost = self._analyze_keyword_context(query_lower, keyword, agent_name)
                score += context_boost
        
        # Apply penalties for conflicting keywords
        for keyword in penalty_keywords:
            if keyword in query_lower:
                score -= 2.0
        
        return max(score, 0.0)  # Ensure non-negative score
    
    def _analyze_keyword_context(self, query: str, keyword: str, agent_name: str) -> float:
        """Analyze context around a keyword to determine agent relevance"""
        # Find keyword position and analyze surrounding words
        keyword_pos = query.find(keyword)
        if keyword_pos == -1:
            return 0.0
        
        # Extract context window (10 characters before and after)
        start = max(0, keyword_pos - 10)
        end = min(len(query), keyword_pos + len(keyword) + 10)
        context = query[start:end]
        
        # Context indicators for each agent
        health_indicators = ["health", "medical", "vaccine", "disease", "doctor", "clinic"]
        visa_indicators = ["visa", "passport", "entry", "travel", "document", "permit"]
        
        if agent_name == "health":
            for indicator in health_indicators:
                if indicator in context:
                    return 2.0
        elif agent_name == "visa":
            for indicator in visa_indicators:
                if indicator in context:
                    return 2.0
        
        # Default small boost for overlapping keywords
        return 0.5
    
    def _routing_decision(self, state: ConversationState) -> str:
        """Decision function for conditional routing"""
        return state.get("current_agent") or "fallback"
    
    async def _process_visa(self, state: ConversationState) -> ConversationState:
        """Process query using visa agent"""
        try:
            visa_agent = self.agents["visa"]
            response = await visa_agent.process(state["query"], state["context"])
            state["response"] = response
            logger.info("Orchestrator: Visa agent processing completed")
        except Exception as e:
            logger.error(f"Orchestrator: Visa agent error: {e}")
            state["response"] = self._create_fallback_response()
        
        return state
    
    async def _process_health(self, state: ConversationState) -> ConversationState:
        """Process query using health agent"""
        try:
            health_agent = self.agents["health"]
            response = await health_agent.process(state["query"], state["context"])
            state["response"] = response
            logger.info("Orchestrator: Health agent processing completed")
        except Exception as e:
            logger.error(f"Orchestrator: Health agent error: {e}")
            state["response"] = self._create_fallback_response()
        
        return state

    async def _fallback_response(self, state: ConversationState) -> ConversationState:
        """Generate fallback response when no agent can handle the query"""
        state["response"] = self._create_fallback_response()
        logger.info("Orchestrator: Fallback response generated")
        return state
    
    def _create_fallback_response(self) -> AgentResponse:
        """Create a generic fallback response"""
        return AgentResponse(
            response="""🌍 **HOT Travel Assistant**

I'm your travel planning assistant! I can help you with:

**Current Capabilities:**
• 🛂 **Visa Requirements** - "Do I need a visa for Japan?"
• 📋 **Documentation** - "What documents do I need?"
• ⏱️ **Processing Times** - "How long does it take?"
• 💰 **Costs** - "What are the fees?"
• 🏨 **Health Requirements** - "What are the health requirements for Japan?"

**Coming Soon:**
• ✈️ Flight information and booking
• 🏨 Hotel recommendations  
• 🌤️ Weather forecasts
• 💱 Currency exchange rates
• 🗺️ Local guides and tips

Try asking me about visa requirements for your destination!""",
            suggestions=[
                "Do I need a visa for Japan?",
                "What are China visa requirements?",
                "How to get India visa?",
                "Do I need Schengen visa?",
                "What are the health requirements for Japan?"
            ],
            agent_type="Orchestrator",
            confidence=0.5,
            metadata={"mode": "fallback", "available_agents": list(self.agents.keys())}
        )
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about all available agents"""
        agent_info = {}
        for name, agent in self.agents.items():
            try:
                agent_info[name] = agent.get_info()
            except Exception as e:
                logger.warning(f"Error getting info for {name} agent: {e}")
                agent_info[name] = {"error": str(e)}
        
        return {
            "orchestrator": {
                "status": "active" if self.graph else "degraded",
                "total_agents": len(self.agents),
                "graph_compiled": self.graph is not None
            },
            "agents": agent_info
        }
    
    def register_agent(self, name: str, agent):
        """
        Register a new agent with the orchestrator.
        
        This allows team members to dynamically add new agents
        without modifying the core orchestrator code.
        
        Args:
            name: Agent identifier
            agent: Agent instance implementing BaseAgent interface
        """
        try:
            self.agents[name] = agent
            logger.info(f"✅ Orchestrator: Registered new agent: {name}")
            
            # Rebuild graph to include new agent
            # Note: In production, you might want more sophisticated hot-reloading
            self._rebuild_graph_with_new_agent(name)
            
        except Exception as e:
            logger.error(f"❌ Orchestrator: Failed to register agent {name}: {e}")
    
    def _rebuild_graph_with_new_agent(self, agent_name: str):
        """Rebuild graph to include newly registered agent"""
        # For now, we'll keep the simple approach
        # In a more sophisticated setup, you'd dynamically add nodes and edges
        logger.info(f"Note: Graph rebuild needed for {agent_name} agent. Restart application for full integration.")


# Global orchestrator instance
orchestrator = TravelOrchestrator()