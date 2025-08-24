"""
Flight Offer Agent

Specialized agent for finding flight offers using the Amadeus API.
This agent extracts flight details from user queries and uses a tool to query the API.
"""

import logging
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from .base_agent import BaseAgent, AgentResponse
import vertexai
from vertexai.generative_models import GenerativeModel, FunctionDeclaration, Tool, Part
from amadeus import Client, ResponseError


logger = logging.getLogger(__name__)

load_dotenv()

AMADEUS_API_KEY = os.environ.get("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.environ.get("AMADEUS_API_SECRET")

query_flight_offers_declaration = FunctionDeclaration(
    name="query_flight_offers",
    description="Returns a list of available flights based on origin, destination, and departure date.",
    parameters={
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Three-letter uppercase airport code for the origin."
            },
            "destination": {
                "type": "string",
                "description": "Three-letter uppercase airport code for the destination."
            },
            "departure_date": {
                "type": "string",
                "description": "Departure date in yyyy-MM-dd format."
            }
        },
        "required": ["origin", "destination", "departure_date"]
    }
)


flight_tool = Tool(function_declarations=[query_flight_offers_declaration])


class FlightOfferAgent(BaseAgent):
    """
    Flight offer agent that uses Amadeus API to find flights.
    """
    
    def __init__(self):
        super().__init__(
            name="Flight Offer Assistant",
            description="Finds flight offers using the Amadeus API based on user queries."
        )
        self.amadeus_client = self._initialize_amadeus_client()
        self.model = self._initialize_ai_model()


    def _query_flight_offers(self, origin: str, destination: str, departure_date: str) -> List[Dict]:
        """
        It returns a list of available flights. This function accepts three parameters:
        origin and destination as uppercase three-letter airport codes, and
        departure_date as a string in the format yyyy-MM-dd such as 2025-09-11.
        """
        if not self.amadeus_client:
            return [{"error": "Amadeus client not initialized. Please check API keys."}]

        try:
            logger.info(f"Querying Amadeus for flights: {origin} -> {destination} on {departure_date}")
            response = self.amadeus_client.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=1,
                max=5
            )
            return response.data
        except ResponseError as error:
            logger.error(f"Amadeus API Error: {error}")
            return [{"error": f"Failed to retrieve flight offers: {error.description}"}]
        except Exception as e:
            logger.error(f"An unexpected error occurred while querying flights: {e}")
            return [{"error": "An unexpected error occurred."}]

    def _initialize_amadeus_client(self):
        """Initialize Amadeus client if API keys are available."""
        if AMADEUS_API_KEY and AMADEUS_API_SECRET and Client:
            try:
                client = Client(
                    client_id=AMADEUS_API_KEY,
                    client_secret=AMADEUS_API_SECRET
                )
                logger.info("✅ Flight Offer Agent: Amadeus client initialized.")
                return client
            except Exception as e:
                logger.error(f"❌ Flight Offer Agent: Failed to initialize Amadeus client: {e}")
                return None
        else:
            logger.warning("ℹ️ Flight Offer Agent: Amadeus API keys not found. Flight search will be disabled.")
            return None

    def _initialize_ai_model(self):
        """Initialize Vertex AI model with flight offer tool."""
        if not self.amadeus_client:
            logger.info("ℹ️ Flight Offer Agent: Skipping AI model initialization as Amadeus client is not available.")
            return None

        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            
            if project_id and vertexai and Tool:
                vertexai.init(project=project_id, location=location)

                system_instruction = """You are a flight details extraction and search assistant.

Your task is to extract the following required fields from user input:

origin: as an IATA airport code (e.g., "CHC").

destination: as an IATA airport code (e.g., "BKK").

departure_date: the date of departure.

If the user provides city names instead of IATA codes for origin or destination, normalize those city names to their correct IATA airport codes (e.g., "Christchurch" → "CHC").

The user may provide the departure date in any format, but you must always convert and format it as yyyy-MM-dd, for example, 2025-09-11.

If any fields are missing, incomplete, or incorrectly formatted, respond by prompting the user to provide the correct information. Do not proceed until all required fields are valid.

If all fields are valid and normalized, you MUST call the tool `flight_tool` using the extracted values. Do not just describe the tool call — actually invoke it using the tool calling mechanism."""

                model = GenerativeModel(model_name, tools=[flight_tool], system_instruction=system_instruction)
                logger.info(f"✅ Flight Offer Agent: Vertex AI initialized with flight tool and system instruction: {project_id} - {model_name}")
                return model
            else:
                logger.info("ℹ️ Flight Offer Agent: Using fallback mode (no AI or required libraries).")
                return None
        except Exception as e:
            logger.error(f"❌ Flight Offer Agent: Failed to initialize Vertex AI: {e}")
            return None
    
    async def can_handle(self, query: str) -> bool:
        """Check if query is flight-related."""
        query_lower = query.lower()
        flight_keywords = [
            "flight", "fly", "ticket", "book a flight", "find a flight",
            "to", "from", "on"
        ]
        # A simple check to see if it looks like a flight query
        return sum(keyword in query_lower for keyword in flight_keywords) >= 2
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process flight-related query using AI and tools."""
        logger.info(f"Flight Offer Agent processing: {query}")
        
        if not self.model:
            return AgentResponse(
                response="I'm sorry, the flight search service is currently unavailable. Please check my configuration.",
                agent_type=self.agent_type,
                confidence=0.2,
                metadata={"mode": "unavailable", "reason": "AI model or Amadeus client not initialized."}
            )

        try:
            return await self._generate_ai_response(query)
        except Exception as e:
            logger.error(f"Flight Offer Agent AI error: {e}")
            return AgentResponse(
                response="Sorry, I encountered an error trying to find flights for you.",
                agent_type=self.agent_type,
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    async def _generate_ai_response(self, query: str) -> AgentResponse:
        """Generate AI-powered response by calling tools for flight offers."""
        try:
            # Generate initial response
            chat = self.model.start_chat()
            response = await chat.send_message_async(query)
            
            # Check if function call is present
            if (hasattr(response, 'candidates') and 
                response.candidates and 
                hasattr(response.candidates[0], 'content') and
                response.candidates[0].content.parts):
                
                part = response.candidates[0].content.parts[0]
                
                # Check if this part contains a function call
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    
                    if function_call.name == "query_flight_offers":
                        # Extract parameters
                        args = function_call.args
                        flight_results = self._query_flight_offers(
                            args.get('origin'),
                            args.get('destination'),
                            args.get('departure_date')
                        )
                        
                        logger.info(f"flight_results raw date: {flight_results}")
                        # Convert function results to a string for the response
                        flight_results_str = self._format_flight_results(flight_results)
                        
                        # Create a response that includes the function results
                        response_text = f"I found these flight options for you:\n\n{flight_results_str}"
                    else:
                        response_text = f"Unknown function requested: {function_call.name}"
                else:
                    response_text = response.text
            else:
                response_text = response.text

            # Format response
            if "price" in response_text.lower() and "total" in response_text.lower():
                response_text = "✈️ **Here are some flight options I found:**\n\n" + response_text

            return AgentResponse(
                response=response_text,
                suggestions=[
                    "Find a flight from London to New York tomorrow",
                    "What are the cheapest flights to Paris next month?",
                    "Book a return ticket from SFO to LAX"
                ],
                agent_type=self.agent_type,
                confidence=0.9,
                metadata={"mode": "ai", "model": "vertex_ai_tool_calling"}
            )

        except Exception as e:
            logger.error(f"Error in AI response generation: {e}")
            return AgentResponse(
                response="Sorry, I encountered an error processing your flight request.",
                agent_type=self.agent_type,
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    def _format_flight_results(self, flight_results: List[Dict]) -> str:
        """Format flight results into a readable string."""
        if not flight_results:
            return "No flights found for your search criteria."
        
        if "error" in flight_results[0]:
            return f"Error: {flight_results[0]['error']}"
        
        formatted_results = []
        for i, flight in enumerate(flight_results[:5], 1):  # Limit to 5 results
            price = flight.get('price', {}).get('total', 'N/A')
            itineraries = flight.get('itineraries', [])
            
            if itineraries:
                segments = itineraries[0].get('segments', [])
                if segments:
                    departure = segments[0].get('departure', {})
                    arrival = segments[-1].get('arrival', {})
                    
                    departure_time = departure.get('at', 'N/A')
                    arrival_time = arrival.get('at', 'N/A')
                    airline = segments[0].get('carrierCode', 'N/A')
                    
                    formatted_results.append(
                        f"{i}. {airline} flight: {departure.get('iataCode', 'N/A')} → {arrival.get('iataCode', 'N/A')}\n"
                        f"   Departure: {departure_time}, Arrival: {arrival_time}\n"
                        f"   Price: ${price}"
                    )
        
        return "\n\n".join(formatted_results) if formatted_results else "No flight details available."
    
    def get_capabilities(self) -> List[str]:
        """Return flight offer agent capabilities."""
        return [
            "Flight offer search",
            "Extracts origin, destination, and date from query",
            "Normalizes city names to IATA codes",
            "Formats dates for API calls",
            "Interfaces with Amadeus API"
        ]