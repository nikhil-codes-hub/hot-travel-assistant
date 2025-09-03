import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import httpx
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent

class HotelAmenity(BaseModel):
    description: str
    chargeable: bool = False

class HotelOffer(BaseModel):
    id: str = Field(..., description="Offer ID")
    check_in_date: str = Field(..., description="Check-in date")
    check_out_date: str = Field(..., description="Check-out date")
    room_quantity: int = Field(..., description="Number of rooms")
    price: Dict[str, Any] = Field(..., description="Price details")
    room: Dict[str, Any] = Field(..., description="Room details")
    guests: Dict[str, Any] = Field(..., description="Guest configuration")
    policies: Dict[str, Any] = Field({}, description="Cancellation and guarantee policies")

class Hotel(BaseModel):
    hotel_id: str = Field(..., description="Hotel ID")
    chain_code: Optional[str] = Field(None, description="Hotel chain code")
    name: str = Field(..., description="Hotel name")
    rating: Optional[float] = Field(None, description="Hotel rating")
    address: Dict[str, Any] = Field(..., description="Hotel address")
    contact: Dict[str, Any] = Field({}, description="Contact information")
    description: Optional[str] = Field(None, description="Hotel description")
    amenities: List[HotelAmenity] = Field([], description="Hotel amenities")
    media: List[Dict[str, Any]] = Field([], description="Hotel images")
    offers: List[HotelOffer] = Field([], description="Available offers")

class HotelSearchResult(BaseModel):
    hotels: List[Hotel]
    search_criteria: Dict[str, Any]
    meta: Dict[str, Any]

class HotelSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("HotelSearchAgent")
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.amadeus_base_url = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
        self.access_token = None
        self.token_expires_at = None
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Search for hotels using Amadeus API
        
        Input:
        - cityCode: City code (PAR, NYC, etc.) or coordinates
        - checkInDate: YYYY-MM-DD
        - checkOutDate: YYYY-MM-DD
        - adults: Number of adult guests per room
        - rooms: Number of rooms (default 1)
        - radius: Search radius in KM
        - radiusUnit: KM or MILE
        - hotelSource: HOTEL_GDS or ALL
        """
        required_fields = ["cityCode", "checkInDate", "checkOutDate", "adults"]
        self.validate_input(input_data, required_fields)
        
        # Check Amadeus API availability
        if not self.amadeus_client_id or not self.amadeus_client_secret:
            self.log("⚠️ Amadeus API credentials not configured, using mock hotel data")
            return self._generate_fallback_hotels(input_data)
        
        try:
            # Ensure we have valid access token
            await self._ensure_access_token()
            
            # First, search for hotels by city
            hotel_list = await self._search_hotels_by_city(input_data)
            
            # Check if no hotels found (common in test environment)
            if not hotel_list:
                self.log("🔄 Using realistic mock hotel data (provides full experience)")
                return self._generate_fallback_hotels(input_data)
            
            # Then get offers for the hotels
            hotels_with_offers = await self._get_hotel_offers(hotel_list, input_data)
            
            # Process and format results
            result = self._process_hotel_results(hotels_with_offers, input_data)
            
            # Add API source indicator
            result["meta"]["data_source"] = "amadeus_api"
            result["meta"]["is_fallback"] = False
            
            self.log(f"✅ Amadeus Hotels API: Retrieved {result['meta']['count']} hotels from live API")
            return self.format_output(result)
            
        except Exception as e:
            error_msg = str(e)
            city_code = input_data.get("cityCode", "unknown")
            latitude, longitude = self._get_city_coordinates(city_code)
            
            if "400" in error_msg and ("NOTHING FOUND" in error_msg or "Nothing found" in error_msg or "NOTHING FOUND FOR REQUESTED CITY" in error_msg):
                self.log(f"ℹ️ Amadeus Hotels API: No hotels available for {city_code} in test environment")
                self.log(f"🗺️ Searched coordinates ({latitude}, {longitude}) - API working correctly")
                self.log("💡 This is expected - Amadeus test API has very limited hotel data")
            elif "400" in error_msg and "INVALID FACILITY" in error_msg:
                self.log(f"⚠️ Amadeus Hotels API: Invalid facility/amenity codes - fixed in next request")
            else:
                self.log(f"⚠️ Amadeus Hotels API error: {e}")
            
            self.log("🔄 Using realistic mock hotel data (provides full experience)")
            return self._generate_fallback_hotels(input_data)
    
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
            expires_in = token_response.get("expires_in", 1799)
            self.token_expires_at = current_time + timedelta(seconds=expires_in - 60)
    
    def _get_city_coordinates(self, flight_city_code: str) -> tuple:
        """Get coordinates for major cities to use with Hotels by Geocode API"""
        coordinates = {
            "ZUR": (47.3769, 8.5417),     # Zurich
            "PAR": (48.8566, 2.3522),     # Paris
            "LON": (51.5074, -0.1278),    # London  
            "NYC": (40.7128, -74.0060),   # New York
            "TYO": (35.6762, 139.6503),   # Tokyo
            "LAX": (34.0522, -118.2437),  # Los Angeles
            "SFO": (37.7749, -122.4194),  # San Francisco
            "BKK": (13.7563, 100.5018),   # Bangkok
            "SIN": (1.3521, 103.8198),    # Singapore
            "DXB": (25.2048, 55.2708),    # Dubai
            "SYD": (-33.8688, 151.2093)   # Sydney
        }
        return coordinates.get(flight_city_code, (48.8566, 2.3522))  # Default to Paris
    
    async def _search_hotels_by_city(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for hotels in a city using Amadeus Hotel List API with coordinates"""
        # Get coordinates for the city instead of using city codes
        original_city_code = input_data["cityCode"]
        latitude, longitude = self._get_city_coordinates(original_city_code)
        
        self.log(f"🏨 Using coordinates for {original_city_code}: ({latitude}, {longitude})")
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "radius": input_data.get("radius", 20),
                "radiusUnit": input_data.get("radiusUnit", "KM"),
                "hotelSource": input_data.get("hotelSource", "ALL")
            }
            
            # Only add amenities and ratings if they have values
            if input_data.get("amenities"):
                params["amenities"] = input_data["amenities"]
            if input_data.get("ratings"):
                params["ratings"] = input_data["ratings"]
            
            response = await client.get(
                f"{self.amadeus_base_url}/v1/reference-data/locations/hotels/by-geocode",
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            # Check for specific API errors before raising
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if error_data.get("errors") and error_data["errors"][0].get("code") == 895:
                        city_code = input_data.get("cityCode", "unknown")
                        self.log(f"ℹ️ Amadeus Hotels API: No hotels available for {city_code} in test environment")
                        self.log(f"🗺️ Searched coordinates ({latitude}, {longitude}) - API working correctly")  
                        self.log("💡 This is expected - Amadeus test API has very limited hotel data")
                        # Return empty list so main flow will handle fallback properly
                        return []
                except:
                    pass  # Fall through to general error handling
            
            response.raise_for_status()
            
            hotels_response = response.json()
            return hotels_response.get("data", [])
    
    async def _get_hotel_offers(self, hotels: List[Dict[str, Any]], input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get hotel offers for specific hotels"""
        if not hotels:
            return []
        
        # Take first 10 hotels to avoid too many API calls
        hotel_ids = [hotel["hotelId"] for hotel in hotels[:10]]
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Build query parameters for GET request
            params = {
                "hotelIds": ",".join(hotel_ids),
                "checkInDate": input_data["checkInDate"],
                "checkOutDate": input_data["checkOutDate"],
                "adults": input_data["adults"],
                "roomQuantity": input_data.get("rooms", 1)
            }
            
            # Add optional parameters
            if input_data.get("currency"):
                params["currency"] = input_data["currency"]
            
            if input_data.get("children"):
                params["children"] = input_data["children"]
            
            response = await client.get(
                f"{self.amadeus_base_url}/v3/shopping/hotel-offers",
                params=params,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            offers_response = response.json()
            return offers_response.get("data", [])
    
    def _process_hotel_results(self, hotels_data: List[Dict[str, Any]], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Amadeus hotel response into our format"""
        try:
            processed_hotels = []
            
            for hotel_data in hotels_data[:input_data.get("max_results", 20)]:
                try:
                    hotel_info = hotel_data.get("hotel", {})
                    offers_data = hotel_data.get("offers", [])
                    
                    # Process amenities
                    amenities = []
                    for amenity_data in hotel_info.get("amenities", []):
                        amenity = HotelAmenity(
                            description=amenity_data.get("description", ""),
                            chargeable=amenity_data.get("chargeable", False)
                        )
                        amenities.append(amenity)
                    
                    # Process offers
                    processed_offers = []
                    for offer_data in offers_data:
                        offer = HotelOffer(
                            id=offer_data["id"],
                            check_in_date=offer_data.get("checkInDate", input_data["checkInDate"]),
                            check_out_date=offer_data.get("checkOutDate", input_data["checkOutDate"]),
                            room_quantity=offer_data.get("roomQuantity", 1),
                            price=offer_data.get("price", {}),
                            room=offer_data.get("room", {}),
                            guests=offer_data.get("guests", {}),
                            policies=offer_data.get("policies", {})
                        )
                        processed_offers.append(offer)
                    
                    # Create hotel object
                    hotel = Hotel(
                        hotel_id=hotel_info.get("hotelId", ""),
                        chain_code=hotel_info.get("chainCode"),
                        name=hotel_info.get("name", ""),
                        rating=hotel_info.get("rating"),
                        address=hotel_info.get("address", {}),
                        contact=hotel_info.get("contact", {}),
                        description=hotel_info.get("description", {}).get("text"),
                        amenities=amenities,
                        media=hotel_info.get("media", []),
                        offers=processed_offers
                    )
                    processed_hotels.append(hotel)
                    
                except Exception as e:
                    self.log(f"Error processing hotel: {e}")
                    continue
            
            result = HotelSearchResult(
                hotels=processed_hotels,
                search_criteria={
                    "cityCode": input_data["cityCode"],
                    "checkInDate": input_data["checkInDate"],
                    "checkOutDate": input_data["checkOutDate"],
                    "adults": input_data["adults"],
                    "children": input_data.get("children", 0),
                    "rooms": input_data.get("rooms", 1)
                },
                meta={
                    "count": len(processed_hotels),
                    "search_radius": input_data.get("radius", 20),
                    "currency": input_data.get("currency", "USD")
                }
            )
            
            return result.model_dump()
            
        except Exception as e:
            raise Exception(f"Error processing hotel response: {e}")
    
    def _generate_fallback_hotels(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock hotel data when Amadeus API is unavailable"""
        
        mock_offers = [
            HotelOffer(
                id="MOCK_HOTEL_OFFER_1",
                check_in_date=input_data["checkInDate"],
                check_out_date=input_data["checkOutDate"],
                room_quantity=input_data.get("rooms", 1),
                price={
                    "currency": "USD",
                    "total": "199.00",
                    "base": "179.00",
                    "taxes": [{"amount": "20.00", "code": "VAT"}]
                },
                room={
                    "type": "STANDARD",
                    "typeEstimated": {
                        "category": "STANDARD_ROOM",
                        "beds": 1,
                        "bedType": "DOUBLE"
                    }
                },
                guests={"adults": input_data["adults"]},
                policies={}
            )
        ]
        
        mock_amenities = [
            HotelAmenity(description="FREE_WIFI", chargeable=False),
            HotelAmenity(description="RESTAURANT", chargeable=False),
            HotelAmenity(description="FITNESS_CENTER", chargeable=False)
        ]
        
        mock_hotels = [
            Hotel(
                hotel_id="MOCK_HOTEL_1",
                chain_code="AC",
                name="Grand City Hotel",
                rating=4.2,
                address={
                    "lines": ["123 Main Street"],
                    "cityName": input_data["cityCode"],
                    "countryCode": "US"
                },
                contact={
                    "phone": "+1-555-0123",
                    "email": "info@grandcityhotel.com"
                },
                description="A comfortable city center hotel with modern amenities",
                amenities=mock_amenities,
                media=[],
                offers=mock_offers
            )
        ]
        
        fallback_result = HotelSearchResult(
            hotels=mock_hotels,
            search_criteria={
                "cityCode": input_data["cityCode"],
                "checkInDate": input_data["checkInDate"],
                "checkOutDate": input_data["checkOutDate"],
                "adults": input_data["adults"],
                "children": input_data.get("children", 0),
                "rooms": input_data.get("rooms", 1)
            },
            meta={
                "count": 1,
                "search_radius": 20,
                "currency": "USD",
                "data_source": "mock_fallback",
                "is_fallback": True,
                "mode": "fallback_mock_data"
            }
        )
        
        self.log("📝 Generated mock hotel data as fallback")
        return self.format_output(fallback_result.model_dump())