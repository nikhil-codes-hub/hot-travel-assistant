"""
Example Flight Agent

This is a template/example showing how team members can create new agents
for the HOT Travel Assistant platform. Copy this file and modify for your agent.
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent, AgentResponse


class FlightAgent(BaseAgent):
    """
    Example flight booking and information agent.
    
    This demonstrates the pattern that team members should follow
    when creating new specialized travel agents.
    """
    
    def __init__(self):
        super().__init__(
            name="Flight Assistant",
            description="Flight booking, information, and travel planning specialist"
        )
        # Initialize any agent-specific resources here
        self.airlines_data = self._load_airlines_data()
    
    def _load_airlines_data(self) -> Dict:
        """Load airline and flight data (placeholder)"""
        return {
            "popular_airlines": ["American", "Delta", "United", "Southwest"],
            "booking_sites": ["Expedia", "Kayak", "Google Flights", "Airline Direct"],
            "tips": [
                "Book 6-8 weeks in advance for best prices",
                "Tuesday and Wednesday are typically cheaper",
                "Clear browser cookies between searches"
            ]
        }
    
    async def can_handle(self, query: str) -> bool:
        """Check if this agent can handle the flight-related query"""
        query_lower = query.lower()
        flight_keywords = [
            "flight", "flights", "airline", "airlines", "booking", "book",
            "airport", "departure", "arrival", "travel", "ticket", "tickets",
            "fare", "price", "schedule", "route", "connection"
        ]
        return any(keyword in query_lower for keyword in flight_keywords)
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process flight-related queries"""
        # Analyze the query to understand what the user wants
        intent = self._analyze_flight_intent(query)
        
        if intent == "booking":
            return self._handle_booking_query(query)
        elif intent == "information":
            return self._handle_info_query(query)
        elif intent == "prices":
            return self._handle_price_query(query)
        else:
            return self._handle_general_query(query)
    
    def _analyze_flight_intent(self, query: str) -> str:
        """Analyze what type of flight assistance the user needs"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["book", "booking", "reserve", "buy"]):
            return "booking"
        elif any(word in query_lower for word in ["price", "cost", "cheap", "fare"]):
            return "prices"
        elif any(word in query_lower for word in ["schedule", "time", "departure", "arrival"]):
            return "information"
        else:
            return "general"
    
    def _handle_booking_query(self, query: str) -> AgentResponse:
        """Handle flight booking requests"""
        return AgentResponse(
            response="""✈️ **Flight Booking Assistant**

I can help you find and book flights! Here's how to get started:

**Best Booking Sites:**
• 🌐 **Google Flights** - Best for comparing prices and routes
• 🌐 **Kayak** - Great for flexible date searches
• 🌐 **Expedia** - Package deals with hotels
• 🏢 **Airline Direct** - Often best for changes/cancellations

**Booking Tips:**
• Book 6-8 weeks in advance for domestic flights
• Tuesday/Wednesday departures are typically cheaper
• Clear cookies between searches for best prices
• Consider nearby airports for savings

**What information do you need to provide?**
• Departure and destination cities
• Travel dates (or flexible date range)
• Number of passengers
• Preferred times or airlines

Ready to search for flights? Tell me your route and dates!""",
            suggestions=[
                "Find flights from NYC to LAX",
                "Book round trip to Europe",
                "Compare airline prices",
                "Help with travel dates"
            ],
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={"intent": "booking", "mode": "example"}
        )
    
    def _handle_price_query(self, query: str) -> AgentResponse:
        """Handle flight price inquiries"""
        return AgentResponse(
            response="""💰 **Flight Price Guide**

**Money-Saving Tips:**
• 📅 **Flexible Dates**: Use +/- 3 day search options
• 🏢 **Compare Airlines**: Budget vs full-service
• 🌍 **Alternative Airports**: Check nearby cities
• 📱 **Price Alerts**: Set up notifications for price drops

**Best Times to Book:**
• **Domestic**: 6-8 weeks in advance
• **International**: 2-3 months in advance
• **Last Minute**: Sometimes deals 1-2 weeks before

**Price Comparison Tools:**
• Google Flights, Kayak, Momondo
• Airline websites directly
• Travel agent consolidators

What route are you looking for? I can help you find the best approach!""",
            suggestions=[
                "Set up price alerts",
                "Compare budget airlines",
                "Find flexible date options",
                "Check alternative airports"
            ],
            agent_type=self.agent_type,
            confidence=0.8,
            metadata={"intent": "prices", "mode": "example"}
        )
    
    def _handle_info_query(self, query: str) -> AgentResponse:
        """Handle flight information requests"""
        return AgentResponse(
            response="""📋 **Flight Information Assistant**

**Flight Details I Can Help With:**
• ✈️ **Schedules**: Departure/arrival times
• 🛂 **Requirements**: Check-in, baggage, documents
• 🎯 **Airlines**: Routes, services, policies
• 🌍 **Airports**: Terminals, connections, amenities

**Useful Resources:**
• Airline websites for real-time updates
• Airport websites for terminal maps
• TSA/security requirements
• Baggage allowance policies

**Planning Your Trip:**
• Arrive 2 hours early (domestic), 3 hours (international)
• Check visa requirements for destination
• Verify passport expiration dates
• Review baggage restrictions

What specific flight information do you need?""",
            suggestions=[
                "Airport check-in requirements",
                "Baggage allowance rules",
                "Flight schedule lookup",
                "Airline policies"
            ],
            agent_type=self.agent_type,
            confidence=0.8,
            metadata={"intent": "information", "mode": "example"}
        )
    
    def _handle_general_query(self, query: str) -> AgentResponse:
        """Handle general flight-related questions"""
        return AgentResponse(
            response="""✈️ **Flight Assistant**

I'm your flight specialist! I can help with:

**Services Available:**
• 🎫 **Booking Assistance** - Find and compare flights
• 💰 **Price Guidance** - Money-saving tips and alerts
• 📋 **Travel Information** - Schedules, requirements, policies
• 🌍 **Route Planning** - Best connections and alternatives

**Popular Requests:**
• "Find cheap flights to Europe"
• "Help me book a round trip to Tokyo"
• "What are baggage fees for Delta?"
• "Best time to fly to avoid crowds"

**Getting Started:**
Just tell me where you want to go and when, and I'll help you find the best options!

What can I help you with today?""",
            suggestions=[
                "Find flights for my trip",
                "Compare airline prices",
                "Get travel requirements",
                "Set up price alerts"
            ],
            agent_type=self.agent_type,
            confidence=0.7,
            metadata={"intent": "general", "mode": "example"}
        )
    
    def get_capabilities(self) -> List[str]:
        """Return flight agent capabilities"""
        return [
            "Flight booking assistance",
            "Price comparison and alerts",
            "Schedule and route information",
            "Airline policy guidance",
            "Travel planning advice",
            "Airport and terminal info"
        ]


# NOTE: This is an example/template file
# Team members should:
# 1. Copy this file to create their own agent
# 2. Modify the class name, capabilities, and logic
# 3. Add to agents/__init__.py
# 4. Register with orchestrator
# 5. Test integration