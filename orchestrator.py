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

from agents import VisaAgent, UserPreferenceAgent, FlightOfferAgent, CustomerPreferenceAgent, HotDealsAgent
from agents.base_agent import AgentResponse, BaseAgent

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
            # Agent for analyzing customer preferences from CSV
            self.agents["hot_deals"] = HotDealsAgent()
            logger.info("✅ Orchestrator: Hot Deals agent initialized")

            # Agent for analyzing customer preferences from CSV
            self.agents["customer_preference"] = CustomerPreferenceAgent(csv_path="customer_travel_dataset.csv")
            logger.info("✅ Orchestrator: Customer Preference agent initialized")

            # More specific agents should be listed first to be checked first.
            self.agents["user_preference"] = UserPreferenceAgent()
            logger.info("✅ Orchestrator: User Preference agent initialized")

            # Flight offer agent
            self.agents["flight_offer"] = FlightOfferAgent()
            logger.info("✅ Orchestrator: Flight Offer agent initialized")

            # Core visa agent
            self.agents["visa"] = VisaAgent()
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
            workflow.add_node("process_user_preference", self._process_user_preference)
            workflow.add_node("process_customer_preference", self._process_customer_preference)
            workflow.add_node("process_flight_offer", self._process_flight_offer)
            workflow.add_node("process_hot_deals", self._process_hot_deals)
            workflow.add_node("fallback_response", self._fallback_response)
            
            # Add edges
            workflow.set_entry_point("route_query")
            
            # Conditional routing based on agent detection
            workflow.add_conditional_edges(
                "route_query",
                self._routing_decision,
                {
                    "hot_deals": "process_hot_deals",
                    "flight_offer": "process_flight_offer",
                    "user_preference": "process_user_preference",
                    "customer_preference": "process_customer_preference",
                    "visa": "process_visa",
                    "fallback": "fallback_response"
                }
            )

            workflow.add_edge("process_hot_deals", END)
            workflow.add_edge("process_flight_offer", END)
            workflow.add_edge("process_customer_preference", END)
            # End after processing
            workflow.add_edge("process_user_preference", END)
            workflow.add_edge("process_visa", END)
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
                # Fallback to direct visa agent if graph failed to initialize
                logger.warning("Orchestrator: Graph not available, using direct visa agent")
                visa_agent = self.agents.get("visa")
                if visa_agent and await visa_agent.can_handle(query):
                    return await visa_agent.process(query)
                else:
                    return self._create_fallback_response()
            
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
        
        # Check each agent's capability to handle the query
        for agent_name, agent in self.agents.items():
            try:
                if await agent.can_handle(query):
                    state["current_agent"] = agent_name
                    state["confidence"] = 0.8
                    logger.info(f"Orchestrator: Routed to {agent_name} agent")
                    return state
            except Exception as e:
                logger.warning(f"Orchestrator: Error checking {agent_name} agent: {e}")
        
        # No specific agent found, use fallback
        state["current_agent"] = "fallback" 
        state["confidence"] = 0.3
        logger.info("Orchestrator: Using fallback response")
        return state
    
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
    
    async def _process_user_preference(self, state: ConversationState) -> ConversationState:
        """Process query using user preference agent"""
        try:
            # Mock user history for demonstration purposes
            # In a real app, this would come from a database based on user_id
            mock_context = {
                "user_history": [
                    {"departureLocation": "NYC", "destinationLocation": "LAX", "cabinClass": "Economy", "booking_date": "2024-01-15T10:00:00Z"},
                    {"departureLocation": "NYC", "destinationLocation": "LAX", "cabinClass": "Economy", "booking_date": "2024-03-20T12:00:00Z"},
                    {"departureLocation": "SFO", "destinationLocation": "TYO", "cabinClass": "Business", "booking_date": "2024-04-05T18:00:00Z"},
                ]
            }
            user_pref_agent = self.agents["user_preference"]
            response = await user_pref_agent.process(state["query"], mock_context)
            state["response"] = response
            logger.info("Orchestrator: User Preference agent processing completed")
        except Exception as e:
            logger.error(f"Orchestrator: User Preference agent error: {e}")
            state["response"] = self._create_fallback_response()
        
        return state

    async def _process_flight_offer(self, state: ConversationState) -> ConversationState:
        """Process query using flight offer agent"""
        try:
            flight_offer_agent = self.agents["flight_offer"]
            response = await flight_offer_agent.process(state["query"], state["context"])
            state["response"] = response
            logger.info("Orchestrator: Flight Offer agent processing completed")
        except Exception as e:
            logger.error(f"Orchestrator: Flight Offer agent error: {e}")
            state["response"] = self._create_fallback_response()
        
        return state

    async def _process_customer_preference(self, state: ConversationState) -> ConversationState:
        """Process query using Customer Preference agent"""
        try:
            customer_preference_agent = self.agents["customer_preference"]
            response = await customer_preference_agent.process(state["query"], state["context"])
            state["response"] = response
            logger.info("Orchestrator: Customer Preference agent processing completed")
        except Exception as e:
            logger.error(f"Orchestrator: Customer Preference agent error: {e}")
            state["response"] = self._create_fallback_response()
        
        return state

    async def _process_hot_deals(self, state: ConversationState) -> ConversationState:
        """Process Hot Deals agent"""
        try:
            hot_deals_agent = self.agents["hot_deals"]
            response = await hot_deals_agent.process(state["query"], state["context"])
            state["response"] = response
            logger.info("Orchestrator: Hot Deals agent processing completed")
        except Exception as e:
            logger.error(f"Orchestrator: Hot Deals agent error: {e}")
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
                "Do I need Schengen visa?"
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