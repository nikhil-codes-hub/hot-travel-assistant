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
        """Generate mock flight data when Amadeus API is unavailable"""
        mock_segments = [
            FlightSegment(
                departure={
                    "iataCode": input_data["origin"],
                    "at": f"{input_data['departure_date']}T08:00:00",
                    "terminal": "1"
                },
                arrival={
                    "iataCode": input_data["destination"],
                    "at": f"{input_data['departure_date']}T14:00:00",
                    "terminal": "2"
                },
                airline="AA",
                flight_number="AA1234",
                aircraft="Boeing 737",
                duration="PT6H00M",
                cabin_class=input_data.get("travel_class", "ECONOMY")
            )
        ]
        
        mock_offers = [
            FlightOffer(
                id="MOCK_OFFER_1",
                price={
                    "currency": "USD",
                    "total": "599.00",
                    "base": "499.00",
                    "fees": [{"amount": "50.00", "type": "SUPPLIER"}],
                    "taxes": [{"amount": "50.00", "code": "US"}]
                },
                segments=mock_segments,
                traveler_pricings=[{
                    "travelerId": "1",
                    "fareOption": "STANDARD",
                    "travelerType": "ADULT",
                    "price": {"currency": "USD", "total": "599.00"}
                }],
                validating_airline="AA",
                instant_ticketing_required=False
            )
        ]
        
        fallback_result = FlightSearchResult(
            offers=mock_offers,
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
                "count": 1,
                "amadeus_count": 0,
                "currency": "USD",
                "data_source": "mock_fallback",
                "is_fallback": True,
                "mode": "fallback_mock_data"
            },
            dictionaries={}
        )
        
        self.log("📝 Generated mock flight data as fallback")
        return self.format_output(fallback_result.model_dump())