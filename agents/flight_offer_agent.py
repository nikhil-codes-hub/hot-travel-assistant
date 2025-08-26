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
import isodate



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

If any fields are missing, incomplete, or incorrect, respond by prompting the user to provide the correct information. Do not proceed until all required fields are valid.

If all fields are valid and normalized, you MUST call the tool `flight_tool` using the extracted values. Do not just describe the tool call — actually invoke it using the tool calling mechanism."""

                model = GenerativeModel(model_name, tools=[flight_tool], system_instruction=system_instruction, generation_config = {"temperature": 0} )
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
    def _get_airline_name(self, code: str) -> str:
        """Returns the full airline name for a given code, or the code if not found."""
        airline_names = {
            "AA": "American Airlines",
            "DL": "Delta Air Lines",
            "UA": "United Airlines",
            "BA": "British Airways",
            "LH": "Lufthansa",
            "AF": "Air France",
            "KL": "KLM Royal Dutch Airlines",
            "EK": "Emirates",
            "QR": "Qatar Airways",
            "SQ": "Singapore Airlines",
            "CA": "Air China",
            "CZ": "China Southern Airlines",
            "MU": "China Eastern Airlines",
            "VS": "Virgin Atlantic",
            "AC": "Air Canada",
            "QF": "Qantas",
            "IB": "Iberia",
            "AY": "Finnair",
            "LX": "Swiss International Air Lines",
            "TK": "Turkish Airlines",
            "AZ": "Alitalia",
            "SK": "Scandinavian Airlines",
            "EI": "Aer Lingus",
            "NZ": "Air New Zealand",
            "SA": "South African Airways",
            "KE": "Korean Air",
            "OZ": "Asiana Airlines",
            "JL": "Japan Airlines",
            "NH": "All Nippon Airways",
            "ET": "Ethiopian Airlines",
            "EY": "Etihad Airways",
            "CX": "Cathay Pacific",
            "GA": "Garuda Indonesia",
            "MH": "Malaysia Airlines",
            "TG": "Thai Airways",
            "VN": "Vietnam Airlines",
            "AM": "Aeromexico",
            "AV": "Avianca",
            "CM": "Copa Airlines",
            "AR": "Aerolineas Argentinas",
            "LA": "LATAM Airlines",
            "JJ": "LATAM Brasil",
            "G3": "GOL Linhas Aéreas",
            "TP": "TAP Air Portugal",
            "BE": "Flybe",
            "DY": "Norwegian Air Shuttle",
            "FR": "Ryanair",
            "U2": "easyJet",
            "W6": "Wizz Air",
            "VX": "Virgin America",
            "B6": "JetBlue Airways",
            "WN": "Southwest Airlines",
            "AS": "Alaska Airlines",
            "HA": "Hawaiian Airlines",
            "F9": "Frontier Airlines",
            "NK": "Spirit Airlines",
            "YX": "Republic Airways",
            "OH": "PSA Airlines",
            "OO": "SkyWest Airlines",
            "MQ": "Envoy Air",
            "YX": "Republic Airways",
            "9E": "Endeavor Air",
            "YV": "Mesa Airlines",
            "AX": "Trans States Airlines",
            "CP": "Compass Airlines",
            "EV": "ExpressJet Airlines",
            "PT": "Piedmont Airlines",
            "OH": "PSA Airlines",
            "YX": "Republic Airways",
            "ZW": "Air Wisconsin",
            "C5": "Champlain Enterprises",
            "EM": "Empire Airlines",
            "FA": "SafariLink Aviation",
            "KQ": "Kenya Airways",
            "LY": "El Al Israel Airlines",
            "OK": "Czech Airlines",
            "PL": "LOT Polish Airlines",
            "RJ": "Royal Jordanian",
            "UL": "SriLankan Airlines",
            "ZH": "Shenzhen Airlines",
            "3U": "Sichuan Airlines",
            "8L": "Lucky Air",
            "9C": "Spring Airlines",
            "JD": "Beijing Capital Airlines",
            "HO": "Juneyao Airlines",
            "KY": "Kunming Airlines",
            "PN": "West Air",
            "UQ": "Urumqi Air",
            "GS": "Tianjin Airlines",
            "DZ": "Air Algerie",
            "KM": "Air Malta",
            "MS": "EgyptAir",
            "SV": "Saudi Arabian Airlines",
            "WY": "Oman Air",
            "GF": "Gulf Air",
            "KU": "Kuwait Airways",
            "ME": "Middle East Airlines",
            "RB": "Syrian Air",
            "YR": "Aria Air",
            "OA": "Olympic Air",
            "JU": "Air Serbia",
            "JP": "Adria Airways",
            "OU": "Croatia Airlines",
            "S7": "S7 Airlines",
            "UT": "UTair Aviation",
            "FV": "Rossiya Airlines",
            "SU": "Aeroflot",
            "PS": "Ukraine International Airlines",
            "A9": "Georgian Airways",
            "HY": "Uzbekistan Airways",
            "KC": "Air Astana",
            "OV": "Estonian Air",
            "BT": "Air Baltic",
            "LO": "LOT Polish Airlines",
            "QS": "Smartwings",
            "TV": "TUI Airways",
            "XQ": "SunExpress",
            "DE": "Condor",
            "4U": "Germanwings",
            "EW": "Eurowings",
            "OS": "Austrian Airlines",
            "SN": "Brussels Airlines",
            "EN": "Air Dolomiti",
            "LG": "Luxair",
            "IB": "Iberia",
            "NT": "Binter Canarias",
            "UX": "Air Europa",
            "HV": "Transavia",
            "VY": "Vueling",
            "OR": "Arkia Israeli Airlines",
            "IZ": "Israir Airlines",
            "UP": "Bahrain Air",
            "9W": "Jet Airways",
            "AI": "Air India",
            "IT": "Kingfisher Airlines",
            "SG": "SpiceJet",
            "6E": "IndiGo",
            "G8": "GoAir",
            "UK": "Vistara",
            "TR": "Scoot",
            "3K": "Jetstar Asia Airways",
            "VF": "Valuair",
            "BL": "Pacific Airlines",
            "UO": "Hong Kong Express Airways",
            "ZE": "Eastar Jet",
            "LJ": "Jin Air",
            "BX": "Air Busan",
            "TW": "T'way Air",
            "RS": "Air Seoul",
            "7C": "Jeju Air",
            "QV": "Lao Airlines",
            "K6": "Cambodia Angkor Air",
            "PG": "Bangkok Airways",
            "FD": "Thai AirAsia",
            "AK": "AirAsia",
            "QZ": "Indonesia AirAsia",
            "PQ": "Philippine Airlines",
            "PR": "Philippine Airlines",
            "5J": "Cebu Pacific",
            "DG": "Cebgo",
            "2P": "Air Philippines",
            "BI": "Royal Brunei Airlines",
            "MH": "Malaysia Airlines",
            "OD": "Malindo Air",
            "JT": "Lion Air",
            "ID": "Batik Air",
            "IW": "Wings Air",
            "QG": "Citilink",
            "SL": "Thai Lion Air",
            "XJ": "Thai AirAsia X",
            "D7": "AirAsia X",
            "XT": "Indonesia AirAsia Extra",
            "TZ": "Scoot",
            "JQ": "Jetstar Airways",
            "DJ": "Virgin Australia",
            "VA": "Virgin Australia",
            "TT": "Tigerair Australia",
            "NZ": "Air New Zealand",
            "PX": "Air Niugini",
            "FJ": "Fiji Airways",
            "NF": "Air Vanuatu",
            "SB": "Aircalin",
            "TN": "Air Tahiti Nui",
            "OF": "Air Kiribati",
            "JM": "Air Jamaica",
            "BW": "Caribbean Airlines",
            "LI": "LIAT",
            "WG": "Sunwing Airlines",
            "TS": "Air Transat",
            "PD": "Porter Airlines",
            "NK": "Spirit Airlines",
            "F9": "Frontier Airlines",
            "YX": "Republic Airways",
            "OH": "PSA Airlines",
            "OO": "SkyWest Airlines",
            "MQ": "Envoy Air",
            "YV": "Mesa Airlines",
            "AX": "Trans States Airlines",
            "CP": "Compass Airlines",
            "EV": "ExpressJet Airlines",
            "PT": "Piedmont Airlines",
            "ZW": "Air Wisconsin",
            "C5": "Champlain Enterprises",
            "EM": "Empire Airlines",
            "FA": "SafariLink Aviation",
            "KQ": "Kenya Airways",
            "LY": "El Al Israel Airlines",
            "OK": "Czech Airlines",
            "PL": "LOT Polish Airlines",
            "RJ": "Royal Jordanian",
            "UL": "SriLankan Airlines",
            "ZH": "Shenzhen Airlines",
            "3U": "Sichuan Airlines",
            "8L": "Lucky Air",
            "9C": "Spring Airlines",
            "JD": "Beijing Capital Airlines",
            "HO": "Juneyao Airlines",
            "KY": "Kunming Airlines",
            "PN": "West Air",
            "UQ": "Urumqi Air",
            "GS": "Tianjin Airlines",
            "DZ": "Air Algerie",
            "KM": "Air Malta",
            "MS": "EgyptAir",
            "SV": "Saudi Arabian Airlines",
            "WY": "Oman Air",
            "GF": "Gulf Air",
            "KU": "Kuwait Airways",
            "ME": "Middle East Airlines",
            "RB": "Syrian Air",
            "YR": "Aria Air",
            "OA": "Olympic Air",
            "JU": "Air Serbia",
            "JP": "Adria Airways",
            "OU": "Croatia Airlines",
            "S7": "S7 Airlines",
            "UT": "UTair Aviation",
            "FV": "Rossiya Airlines",
            "SU": "Aeroflot",
            "PS": "Ukraine International Airlines",
            "A9": "Georgian Airways",
            "HY": "Uzbekistan Airways",
            "KC": "Air Astana",
            "OV": "Estonian Air",
            "BT": "Air Baltic",
            "LO": "LOT Polish Airlines",
            "QS": "Smartwings",
            "TV": "TUI Airways",
            "XQ": "SunExpress",
            "DE": "Condor",
            "4U": "Germanwings",
            "EW": "Eurowings",
            "OS": "Austrian Airlines",
            "SN": "Brussels Airlines",
            "EN": "Air Dolomiti",
            "LG": "Luxair",
            "IB": "Iberia",
            "NT": "Binter Canarias",
            "UX": "Air Europa",
            "HV": "Transavia",
            "VY": "Vueling",
            "OR": "Arkia Israeli Airlines",
            "IZ": "Israir Airlines",
            "UP": "Bahrain Air",
            "9W": "Jet Airways",
            "AI": "Air India",
            "IT": "Kingfisher Airlines",
            "SG": "SpiceJet",
            "6E": "IndiGo",
            "G8": "GoAir",
            "UK": "Vistara",
            "TR": "Scoot",
            "3K": "Jetstar Asia Airways",
            "VF": "Valuair",
            "BL": "Pacific Airlines",
            "UO": "Hong Kong Express Airways",
            "ZE": "Eastar Jet",
            "LJ": "Jin Air",
            "BX": "Air Busan",
            "TW": "T'way Air",
            "RS": "Air Seoul",
            "7C": "Jeju Air",
            "QV": "Lao Airlines",
            "K6": "Cambodia Angkor Air",
            "PG": "Bangkok Airways",
            "FD": "Thai AirAsia",
            "AK": "AirAsia",
            "QZ": "Indonesia AirAsia",
            "PQ": "Philippine Airlines",
            "PR": "Philippine Airlines",
            "5J": "Cebu Pacific",
            "DG": "Cebgo",
            "2P": "Air Philippines",
            "BI": "Royal Brunei Airlines",
            "MH": "Malaysia Airlines",
            "OD": "Malindo Air",
            "JT": "Lion Air",
            "ID": "Batik Air",
            "IW": "Wings Air",
            "QG": "Citilink",
            "SL": "Thai Lion Air",
            "XJ": "Thai AirAsia X",
            "D7": "AirAsia X",
            "XT": "Indonesia AirAsia Extra",
            "TZ": "Scoot",
            "JQ": "Jetstar Airways",
            "DJ": "Virgin Australia",
            "VA": "Virgin Australia",
            "TT": "Tigerair Australia",
            "NZ": "Air New Zealand",
            "PX": "Air Niugini",
            "FJ": "Fiji Airways",
            "NF": "Air Vanuatu",
            "SB": "Aircalin",
            "TN": "Air Tahiti Nui",
            "OF": "Air Kiribati",
            "JM": "Air Jamaica",
            "BW": "Caribbean Airlines",
            "LI": "LIAT",
            "WG": "Sunwing Airlines",
            "TS": "Air Transat",
            "PD": "Porter Airlines",
        }
        return airline_names.get(code)


    def _format_duration(self, iso_duration_str: str) -> str:
        # Parse the ISO 8601 duration string
        duration = isodate.parse_duration(iso_duration_str)
        
        # Convert to total seconds
        total_seconds = int(duration.total_seconds())
        
        # Calculate days, hours, and minutes
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        # Format the output string
        if days > 0:
            return f"{days} days, {hours} hours and {minutes} minutes"
        else:
            return f"{hours} hours and {minutes} minutes"


    def _format_flight_results(self, flight_results: List[Dict]) -> str:
        """
        Format flight results into a readable string, showing all flight segments
        and full airline names.
        """
        if not flight_results:
            return "No flights found for your search criteria."

        if "error" in flight_results[0]:
            return f"Error: {flight_results[0]['error']}"

        formatted_results = []
        for i, flight in enumerate(flight_results[:5], 1):  # Limit to 5 results
            price = flight.get('price', {}).get('total', 'N/A')
            itineraries = flight.get('itineraries', [])

            if itineraries:
                # Assuming we only display the first itinerary for simplicity,
                # as a flight result typically represents one complete option.
                first_itinerary = itineraries[0]

                segments = first_itinerary.get('segments', [])
                iso_duration = first_itinerary.get('duration', '')
                duration = self._format_duration(iso_duration)

                if segments:
                    flight_summary_lines = [f"{i}. Price: ${price} Duration: {duration}"]

                    # Add each segment's details
                    for j, segment in enumerate(segments, 1):
                        airline_code = segment.get('carrierCode', 'N/A')
                        airline_name = self._get_airline_name(airline_code)
                        departure = segment.get('departure', {})
                        arrival = segment.get('arrival', {})

                        departure_airport = departure.get('iataCode', 'N/A')
                        arrival_airport = arrival.get('iataCode', 'N/A')
                        departure_time = departure.get('at', 'N/A')
                        arrival_time = arrival.get('at', 'N/A')
                        flight_number = segment.get('number', 'N/A')

                        segment_line = (
                            f"   Segment {j}: {airline_name} (Flight {airline_code}{flight_number})\n"
                            f"      {departure_airport} ({departure_time}) → {arrival_airport} ({arrival_time})"
                        )
                        flight_summary_lines.append(segment_line)

                    formatted_results.append("\n".join(flight_summary_lines))

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