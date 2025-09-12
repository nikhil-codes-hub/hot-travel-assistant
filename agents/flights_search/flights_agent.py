import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import httpx
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class FlightSegment(BaseModel):
    departure: Dict[str, Any] = Field(..., description="Departure details")
    arrival: Dict[str, Any] = Field(..., description="Arrival details")
    airline: str = Field(..., description="Airline code")
    flight_number: str = Field(..., description="Flight number")
    aircraft: Optional[str] = Field(None, description="Aircraft type")
    duration: str = Field(..., description="Flight duration")
    cabin_class: str = Field(..., description="Booking class")

class FlightOffer(BaseModel):
    id: str = Field(..., description="Offer ID")
    price: Dict[str, Any] = Field(..., description="Price details")
    segments: List[FlightSegment] = Field(..., description="Flight segments")
    traveler_pricings: List[Dict[str, Any]] = Field(..., description="Pricing per traveler")
    validating_airline: str = Field(..., description="Validating airline")
    instant_ticketing_required: bool = Field(False, description="Ticketing requirement")

class FlightSearchResult(BaseModel):
    offers: List[FlightOffer]
    search_criteria: Dict[str, Any]
    meta: Dict[str, Any]
    dictionaries: Dict[str, Any]

class FlightsSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("FlightsSearchAgent")
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.amadeus_base_url = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
        self.access_token = None
        self.token_expires_at = None
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Search for flights using Amadeus API
        
        Input:
        - origin: Origin airport code
        - destination: Destination airport code
        - departure_date: YYYY-MM-DD
        - return_date: YYYY-MM-DD (optional for one-way)
        - adults: Number of adult passengers
        - children: Number of child passengers (optional)
        - travel_class: ECONOMY/PREMIUM_ECONOMY/BUSINESS/FIRST
        - max_results: Maximum number of offers to return
        """
        required_fields = ["origin", "destination", "departure_date", "adults"]
        self.validate_input(input_data, required_fields)
        
        # Check Amadeus API availability
        if not self.amadeus_client_id or not self.amadeus_client_secret:
            self.log("⚠️ Amadeus API credentials not configured, using mock flight data")
            return self._generate_fallback_flights(input_data)
        
        try:
            # Ensure we have valid access token
            await self._ensure_access_token()
            
            # Build search parameters
            search_params = self._build_search_params(input_data)
            
            # Call Amadeus Flight Offers Search
            offers_response = await self._search_flight_offers(search_params)
            
            # Process and format results
            result = self._process_flight_offers(offers_response, input_data)
            
            # Check if API returned no offers (common for test routes)
            if result["meta"]["count"] == 0:
                origin = input_data.get("origin", "Unknown")
                destination = input_data.get("destination", "Unknown")
                self.log(f"ℹ️ Amadeus Flights API: No flights available for {origin}→{destination} in test environment")
                self.log("💡 This is expected - test API has limited route coverage")
                self.log("🔄 Using realistic mock flight data (provides full experience)")
                return self._generate_fallback_flights(input_data)
            
            # Add API source indicator
            result["meta"]["data_source"] = "amadeus_api"
            result["meta"]["is_fallback"] = False
            
            self.log(f"✅ Amadeus Flights API: Retrieved {result['meta']['count']} offers from live API")
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"⚠️ Amadeus API error: {e}")
            self.log("🔄 Falling back to mock flight data")
            return self._generate_fallback_flights(input_data)
    
    async def _ensure_access_token(self):
        """Ensure we have a valid Amadeus access token"""
        current_time = datetime.now(timezone.utc)
        
        if self.access_token and self.token_expires_at:
            if current_time < self.token_expires_at:
                return  # Token is still valid
        
        # Get new access token
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.amadeus_client_id,
                "client_secret": self.amadeus_client_secret
            }
            
            response = await client.post(
                f"{self.amadeus_base_url}/v1/security/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 1799)  # Default ~30 mins
            self.token_expires_at = current_time + timedelta(seconds=expires_in - 60)
    
    def _build_search_params(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Amadeus API search parameters"""
        params = {
            "originLocationCode": input_data["origin"],
            "destinationLocationCode": input_data["destination"],
            "departureDate": input_data["departure_date"],
            "adults": input_data["adults"],
            "max": input_data.get("max_results", 20),
            "currencyCode": input_data.get("currency", "USD")
        }
        
        # Optional parameters
        if input_data.get("return_date"):
            params["returnDate"] = input_data["return_date"]
        
        if input_data.get("children"):
            params["children"] = input_data["children"]
        
        if input_data.get("travel_class"):
            params["travelClass"] = input_data["travel_class"].upper()
        
        if input_data.get("non_stop"):
            params["nonStop"] = "true"
        
        return params
    
    async def _search_flight_offers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call Amadeus Flight Offers Search API"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.amadeus_base_url}/v2/shopping/flight-offers",
                params=params,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    def _process_flight_offers(self, amadeus_response: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Amadeus response into our format"""
        try:
            offers_data = amadeus_response.get("data", [])
            dictionaries = amadeus_response.get("dictionaries", {})
            meta = amadeus_response.get("meta", {})
            
            processed_offers = []
            for offer_data in offers_data[:input_data.get("max_results", 20)]:
                try:
                    # Process segments
                    segments = []
                    for itinerary in offer_data.get("itineraries", []):
                        for segment_data in itinerary.get("segments", []):
                            segment = FlightSegment(
                                departure={
                                    "iataCode": segment_data["departure"]["iataCode"],
                                    "at": segment_data["departure"]["at"],
                                    "terminal": segment_data["departure"].get("terminal")
                                },
                                arrival={
                                    "iataCode": segment_data["arrival"]["iataCode"],
                                    "at": segment_data["arrival"]["at"],
                                    "terminal": segment_data["arrival"].get("terminal")
                                },
                                airline=segment_data["carrierCode"],
                                flight_number=f"{segment_data['carrierCode']}{segment_data['number']}",
                                aircraft=segment_data.get("aircraft", {}).get("code"),
                                duration=segment_data["duration"],
                                cabin_class=segment_data.get("cabin", "ECONOMY")
                            )
                            segments.append(segment)
                    
                    # Create offer
                    offer = FlightOffer(
                        id=offer_data["id"],
                        price=offer_data["price"],
                        segments=segments,
                        traveler_pricings=offer_data.get("travelerPricings", []),
                        validating_airline=offer_data.get("validatingAirlineCodes", [""])[0],
                        instant_ticketing_required=offer_data.get("instantTicketingRequired", False)
                    )
                    processed_offers.append(offer)
                    
                except Exception as e:
                    self.log(f"Error processing offer: {e}")
                    continue
            
            result = FlightSearchResult(
                offers=processed_offers,
                search_criteria={
                    "origin": input_data["origin"],
                    "destination": input_data["destination"],
                    "departure_date": input_data["departure_date"],
                    "return_date": input_data.get("return_date"),
                    "passengers": {
                        "adults": input_data["adults"],
                        "children": input_data.get("children", 0)
                    },
                    "travel_class": input_data.get("travel_class")
                },
                meta={
                    "count": len(processed_offers),
                    "amadeus_count": len(offers_data),
                    "currency": amadeus_response.get("meta", {}).get("currency", "USD")
                },
                dictionaries=dictionaries
            )
            
            return result.model_dump()
            
        except Exception as e:
            raise Exception(f"Error processing Amadeus response: {e}")
    
    def _generate_fallback_flights(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic mock flight data when Amadeus API is unavailable"""
        # Define airlines and their details for different routes
        airlines = [
            {"code": "AI", "name": "Air India", "alliance": "STAR"},
            {"code": "UK", "name": "Vistara", "alliance": "STAR"},
            {"code": "EK", "name": "Emirates", "alliance": "none"},
            {"code": "QR", "name": "Qatar Airways", "alliance": "ONEWORLD"},
            {"code": "BA", "name": "British Airways", "alliance": "ONEWORLD"},
            {"code": "LH", "name": "Lufthansa", "alliance": "STAR"}
        ]
        
        # Define aircraft types for realism
        aircraft_types = ["Boeing 777-300ER", "Boeing 787-9 Dreamliner", "Airbus A350-900", 
                         "Airbus A380-800", "Boeing 747-8"]
        
        mock_offers = []
        
        # Generate 3 different flight options
        for i in range(3):
            airline = airlines[i % len(airlines)]
            flight_number = f"{airline['code']}{100 + i}"
            base_price = 1200 + (i * 200)  # Vary prices
            total_price = base_price * input_data.get("adults", 1)
            
            # Format price as string with currency
            price_str = f"USD {total_price:.2f}"
            
            # Create route string
            origin_city = "Los Angeles" if input_data.get("origin") == "LAX" else "New York"
            dest_city = "New Delhi" if "DEL" in input_data.get("destination", "") else "Jaipur"
            route = f"{origin_city} ({input_data.get('origin', '')}) to {dest_city} ({input_data.get('destination', '')})"
            
            # Create flight offer in the expected format
            flight_offer = {
                "rank": i + 1,
                "airline": airline["name"],
                "price": price_str,
                "route": route,
                "connections": 1 if i > 0 else 0,  # First option is direct, others have 1 connection
                "recommendation_reason": "Best value" if i == 0 else "Good alternative" if i == 1 else "Economy option",
                "departure_time": f"{10 + i}:00",
                "arrival_time": f"{12 + (i*2) % 12 + 12}:00",
                "duration": f"{14 + i % 4}h {30 + (i*13) % 60:02d}m",
                "aircraft": aircraft_types[i % len(aircraft_types)],
                "cabin_class": input_data.get("travel_class", "ECONOMY").capitalize(),
                "baggage_allowance": "2 x 23kg" if input_data.get("travel_class") == "BUSINESS" else "1 x 23kg",
                "refundable": i < 2,  # First two options are refundable
                "flight_number": flight_number
            }
            
            mock_offers.append(flight_offer)
        
        # Sort by price
        mock_offers.sort(key=lambda x: float(x["price"].replace("USD ", "")))
        
        # Update ranks after sorting
        for i, offer in enumerate(mock_offers):
            offer["rank"] = i + 1
        
        # Return in the expected format
        return {
            "data": {
                "offers": mock_offers
            },
            "meta": {
                "count": len(mock_offers),
                "is_fallback": True,
                "currency": "USD"
            }
        }