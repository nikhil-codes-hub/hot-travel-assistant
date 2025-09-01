"""
Flight Offers Agent

Specialized agent for handling Flight Offers search requirements and related queries.
Extracted from the original app.py to enable modular agent architecture.
"""

import os, json, logging
from typing import Dict, List, Optional
from .base_agent import BaseAgent, AgentResponse
from tabulate import tabulate
from amadeus import Client, ResponseError
from dotenv import load_dotenv
from datetime import datetime
from rich.table import Table
from rich.console import Console

# Load environment variables
load_dotenv()

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
except ImportError:
    vertexai = None
    GenerativeModel = None

logger = logging.getLogger(__name__)

class FlightOffersAgent(BaseAgent):
    """
    Flight booking and information agent integrated with Gemini + Amadeus API.
    """

    def __init__(self):
        logger.info("Inside init of Flight offers")
        super().__init__(
            name="Flight Offers Assistant",
            description="Find flights, prices, and schedules using Amadeus API"
        )
        self.agent_type = "flight_offers"
        logger.info("Calling initialize AI model func")
        self.model = self._initialize_ai_model()
        logger.info("After that")
        self.amadeus = Client(
            client_id="YOUR_API_KEY",
            client_secret="YOUR_API_SECRET"
        )
        #self.flight_offers_data = self._load_flight_offers_database()

    def _initialize_ai_model(self):
        """Initialize Vertex AI model if available and authorized"""
        logger.info("Initializing AI Model")
        try:
            logger.info("Inside try block")
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            
            if project_id and vertexai:
                logger.info("Fetching project_id")
                vertexai.init(project=project_id, location=location)
                model = GenerativeModel(model_name)
                logger.info(f"✅ Flight Offers Agent: Vertex AI initialized: {project_id} - {model_name}")
                return model
            else:
                logger.info("ℹ️ Flight Offers Agent: Using fallback mode (no AI)")
                return None
        except Exception as e:
            logger.error(f"❌ Flight Offers Agent: Failed to initialize Vertex AI: {e}")
            return None

    async def can_handle(self, query: str) -> bool:
        """Decide if this agent should handle the query"""
        keywords = ["flight", "flights", "airline", "book", "price", "schedule", "offers", "offer", "travel"]
        return any(k in query.lower() for k in keywords)

    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Directly parse user query → extract params → call Amadeus API"""
        logger.info("processing flight_offer")
        params = await self._parse_query_with_gemini(query)
        if not params.get("origin") or not params.get("destination") or not params.get("departure_date"):
            logger.info("No parameters")
            return AgentResponse(
                response="Please provide origin, destination, and departure date to search for flights.",
                agent_type=self.agent_type,
                confidence=0.8
            )

        flights = self._search_flights(params["origin"], params["destination"], params["departure_date"])
        return AgentResponse(
            response=self._format_flights(flights),
            agent_type=self.agent_type,
            confidence=0.9
        )

    def _fallback_parse_query(self, query: str) -> Dict:
        """Simple regex-based parsing when AI is not available"""
        import re
        
        params = {}
        
        # Look for airport codes (3 letters)
        airport_codes = re.findall(r'\b[A-Z]{3}\b', query.upper())
        if len(airport_codes) >= 2:
            params["origin"] = airport_codes[0]
            params["destination"] = airport_codes[1]
        
        # Look for dates (YYYY-MM-DD format)
        date_match = re.search(r'\b\d{4}-\d{2}-\d{2}\b', query)
        if date_match:
            params["departure_date"] = date_match.group()
        
        logger.info(f"Fallback parsing extracted: {params}")
        return params

    async def _parse_query_with_gemini(self, query: str) -> Dict:
        """Use Gemini to extract flight parameters from query"""
        logger.info("parse query with gemini")
        prompt = f"""
        You are an assistant that extracts flight information. The current year is 2025.
        Extract flight search parameters from this query and return ONLY valid JSON:
        Don't assume a past date - use future dates only.
        {{
            "origin": "3-letter airport code",
            "destination": "3-letter airport code", 
            "departure_date": "YYYY-MM-DD format"
        }}
        Query: "{query}"
        """
        #model = genai.GenerativeModel("gemini-pro")
        #response = model.generate_content(prompt)

        self.model = self._initialize_ai_model()

        self.amadeus = Client(
            client_id="YOUR_API_KEY",
            client_secret="YOUR_API_SECRET"
        )

        try:
            logger.info("In try block")
            if not self.model:
                logger.info("Return empty")
                return {}
            logger.info("Fetching response")
            response = self.model.generate_content(prompt)
            logger.info("Fetched the response")

            if not response.candidates:
                logger.warning("No candidates in response")
                return self._fallback_parse_query(query)

            text = response.candidates[0].content.parts[0].text

            logger.info(f"Raw AI response: '{text}'")

            # Clean the response - remove markdown formatting
            import re
            
            # Remove markdown code blocks
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
            text = text.strip()
            
            logger.info(f"Cleaned text: '{text}'")

            logger.info(f"Response length: {len(text)}")
            logger.info(f"Response type: {type(text)}")

            logger.info("Fetching text")
            return json.loads(text)
        except Exception as e:
            logger.error(f"Gemini parsing failed: {e}")
            logger.info("Falling back to regex parsing")
            return self._fallback_parse_query(query)

    def _search_flights(self, origin: str, destination: str, date: str):
        """Call Amadeus API to search flights"""
        try:
            res = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=date,
                adults=1,
                max=3
            )
            return res.data
        except ResponseError:
            return []

    def _format_flights(self, flights) -> str:
        """Format flights as a simple list instead of a table."""
        if not flights:
            return "No flights found for the given route and date."

        output_lines = []
        for i, offer in enumerate(flights, start=1):
            if "itineraries" not in offer or "price" not in offer:
                continue

            price = f"€{float(offer['price']['total']):,.2f}"
            output_lines.append(f"Flight {i}: {price}")

            for it in offer["itineraries"]:
                for seg in it["segments"]:
                    dep_time = datetime.fromisoformat(seg["departure"]["at"]).strftime("%Y-%m-%d %H:%M")
                    arr_time = datetime.fromisoformat(seg["arrival"]["at"]).strftime("%Y-%m-%d %H:%M")
                    output_lines.append(f"   From {seg['departure']['iataCode']} at {dep_time}")
                    output_lines.append(f"   To   {seg['arrival']['iataCode']} at {arr_time}")
                    output_lines.append("")  # Blank line for spacing

        return "\n".join(output_lines)

    def get_capabilities(self) -> List[str]:
        return [
            "Search flights via Amadeus API",
            "Parse queries using Gemini",
            "Price lookup",
            "Flight schedule info"
        ]
