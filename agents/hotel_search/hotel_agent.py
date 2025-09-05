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
        self.log(f"Hotel Search Agent: Executing with input data: {input_data}")
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
            self.log("⚠️ Amadeus API credentials not configured - hotels unavailable")
            return self._generate_no_hotels_message(input_data)
        
        try:
            # Ensure we have valid access token
            await self._ensure_access_token()
            
            # First, search for hotels by city
            hotel_list = await self._search_hotels_by_city(input_data)
            
            # Check if no hotels found (common in test environment)
            if not hotel_list:
                self.log("❌ No hotels found in destination - hotels unavailable")
                return self._generate_no_hotels_message(input_data)
            
            # Then try to get offers for the hotels
            hotels_with_offers = await self._get_hotel_offers(hotel_list, input_data)
            
            # Process and format results - combine hotels with offers when available
            result = self._process_hotel_results_with_fallback(hotel_list, hotels_with_offers, input_data)
            
            # Add API source indicator
            result["meta"]["data_source"] = "amadeus_api"
            result["meta"]["is_fallback"] = False
            
            self.log(f"✅ Amadeus Hotels API: Retrieved {result['meta']['count']} hotels from live API")
            return self.format_output(result)
            
        except Exception as e:
            error_msg = str(e)
            city_code = input_data.get("cityCode", "unknown")
            latitude, longitude = await self._get_city_coordinates(city_code)
            
            if "400" in error_msg and ("NOTHING FOUND" in error_msg or "Nothing found" in error_msg or "NOTHING FOUND FOR REQUESTED CITY" in error_msg):
                self.log(f"ℹ️ Amadeus Hotels API: No hotels available for {city_code} in test environment")
                self.log(f"🗺️ Searched coordinates ({latitude}, {longitude}) - API working correctly")
                self.log("💡 This is expected - Amadeus test API has very limited hotel data")
            elif "400" in error_msg and "INVALID FACILITY" in error_msg:
                self.log(f"⚠️ Amadeus Hotels API: Invalid facility/amenity codes - fixed in next request")
            else:
                self.log(f"⚠️ Amadeus Hotels API error: {e}")
            
            self.log("❌ No hotels found from live API - returning unavailable message")
            return self._generate_no_hotels_message(input_data)
    
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
            self.log(f"Access token: {self.access_token}")
            expires_in = token_response.get("expires_in", 1799)
            self.token_expires_at = current_time + timedelta(seconds=expires_in - 60)
    
    async def _get_city_coordinates(self, flight_city_code: str) -> tuple:
        """Get coordinates for cities dynamically using geocoding API"""
        # First try known airport/city code mappings for faster response
        known_coordinates = {
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
            "SYD": (-33.8688, 151.2093),  # Sydney
            "DEL": (28.6139, 77.2090),    # Delhi
            "BOM": (19.0760, 72.8777),    # Mumbai
            "BLR": (12.9716, 77.5946),    # Bengaluru
            "MAA": (13.0827, 80.2707),    # Chennai
            "CCU": (22.5726, 88.3639),    # Kolkata
            "HYD": (17.3850, 78.4867),    # Hyderabad
            "AMD": (23.0225, 72.5714),    # Ahmedabad
            "PNQ": (18.5204, 73.8567),    # Pune
            "GOI": (15.3805, 73.8370),    # Goa
            "COK": (9.9312, 76.2673),     # Kochi
        }
        
        # If we have the coordinates cached, return them
        if flight_city_code in known_coordinates:
            coordinates = known_coordinates[flight_city_code]
            self.log(f"🗺️ Using cached coordinates for {flight_city_code}: {coordinates}")
            return coordinates
        
        # Try to get coordinates dynamically via geocoding
        try:
            # Map common airport codes to city names for geocoding
            city_name_mapping = {
                "JFK": "New York", "LGA": "New York", "EWR": "New York",
                "LAX": "Los Angeles", "SFO": "San Francisco", "OAK": "San Francisco",
                "ORD": "Chicago", "MDW": "Chicago", "DFW": "Dallas", "IAH": "Houston",
                "ATL": "Atlanta", "MIA": "Miami", "MCO": "Orlando", "LAS": "Las Vegas",
                "SEA": "Seattle", "DEN": "Denver", "PHX": "Phoenix", "BOS": "Boston",
                "IAD": "Washington DC", "DCA": "Washington DC", "BWI": "Baltimore",
                "CDG": "Paris", "ORY": "Paris", "LHR": "London", "LGW": "London",
                "STN": "London", "FCO": "Rome", "VCE": "Venice", "MXP": "Milan",
                "FRA": "Frankfurt", "MUC": "Munich", "AMS": "Amsterdam", "MAD": "Madrid",
                "BCN": "Barcelona", "LIS": "Lisbon", "ZUR": "Zurich", "VIE": "Vienna",
                "CPH": "Copenhagen", "ARN": "Stockholm", "OSL": "Oslo", "HEL": "Helsinki",
                "NRT": "Tokyo", "HND": "Tokyo", "KIX": "Osaka", "ICN": "Seoul",
                "PVG": "Shanghai", "PEK": "Beijing", "HKG": "Hong Kong", "TPE": "Taipei",
                "BOM": "Mumbai", "DEL": "Delhi", "BLR": "Bengaluru", "MAA": "Chennai",
                "CCU": "Kolkata", "HYD": "Hyderabad", "AMD": "Ahmedabad", "PNQ": "Pune",
                "GOI": "Goa", "COK": "Kochi", "TRV": "Thiruvananthapuram", "GAU": "Guwahati"
            }
            
            # Get city name from airport code or use the code itself
            city_name = city_name_mapping.get(flight_city_code, flight_city_code)
            
            # Normalize city names for consistent geocoding
            city_name_normalizations = {
                "bangalore": "bengaluru",
                "bombay": "mumbai", 
                "madras": "chennai",
                "calcutta": "kolkata",
                "poona": "pune",
                "mysore": "mysuru",
                "cochin": "kochi",
                "trivandrum": "thiruvananthapuram",
                "baroda": "vadodara",
                "allahabad": "prayagraj"
            }
            
            # Apply normalization (case-insensitive)
            city_name_lower = city_name.lower()
            if city_name_lower in city_name_normalizations:
                normalized_name = city_name_normalizations[city_name_lower]
                self.log(f"🔄 Normalizing '{city_name}' → '{normalized_name}'")
                city_name = normalized_name
            
            self.log(f"🔍 Geocoding {flight_city_code} -> '{city_name}' using Nominatim API")
            
            # Use OpenStreetMap Nominatim (free geocoding service)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": city_name,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1
                    },
                    headers={
                        "User-Agent": "HOT-Travel-Assistant/1.0"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    latitude = float(result["lat"])
                    longitude = float(result["lon"])
                    
                    self.log(f"✅ Geocoded {flight_city_code} ({city_name}): ({latitude}, {longitude})")
                    return (latitude, longitude)
                else:
                    self.log(f"⚠️ No geocoding results found for {flight_city_code} ({city_name})")
                    
        except Exception as e:
            self.log(f"⚠️ Geocoding failed for {flight_city_code}: {e}")
        
        # Fallback to Paris coordinates if everything fails
        self.log(f"🔄 Using fallback coordinates (Paris) for {flight_city_code}")
        return (48.8566, 2.3522)  # Paris as last resort
    
    async def _search_hotels_by_city(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for hotels in a city using Amadeus Hotel List API with coordinates"""
        # Get coordinates for the city instead of using city codes
        original_city_code = input_data["cityCode"]
        latitude, longitude = await self._get_city_coordinates(original_city_code)
        
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
        """Get hotel offers for specific hotels - fetch each hotel individually"""
        if not hotels:
            return []
        
        # Take first 5 hotels to avoid too many API calls
        selected_hotels = hotels[:5]
        all_hotel_offers = []
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Loop through each hotel and get offers individually
            for hotel in selected_hotels:
                hotel_id = hotel.get("hotelId")
                if not hotel_id:
                    continue
                    
                # Build query parameters for individual hotel
                params = {
                    "hotelIds": hotel_id,  # Single hotel ID
                    "checkInDate": input_data["checkInDate"],
                    "checkOutDate": input_data["checkOutDate"],
                    "adults": input_data["adults"],
                    "roomQuantity": input_data.get("rooms", 1),
                    "currency": input_data.get("currency", "USD")
                }
                
                # Add optional parameters
                if input_data.get("children"):
                    params["children"] = input_data["children"]
                
                # Log the request for this specific hotel
                request_url = f"{self.amadeus_base_url}/v3/shopping/hotel-offers"
                self.log(f"🏨 Fetching offers for hotel {hotel_id}: {hotel.get('name', 'Unknown')}")
                
                try:
                    response = await client.get(
                        request_url,
                        params=params,
                        headers=headers,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    
                    offers_response = response.json()
                    hotel_offers = offers_response.get("data", [])
                    
                    if hotel_offers:
                        all_hotel_offers.extend(hotel_offers)
                        self.log(f"✅ Found {len(hotel_offers)} offers for {hotel_id}")
                    else:
                        self.log(f"⚠️ No offers available for hotel {hotel_id}")
                    
                except httpx.HTTPStatusError as e:
                    self.log(f"❌ HTTP error for hotel {hotel_id}: {e.response.status_code}")
                    if e.response.status_code == 400:
                        # Log the error details for 400 errors
                        try:
                            error_data = e.response.json()
                            self.log(f"API Error details: {error_data}")
                        except:
                            pass
                    continue
                    
                except Exception as e:
                    self.log(f"❌ Unexpected error for hotel {hotel_id}: {e}")
                    continue
            
            self.log(f"🏨 Total hotel offers collected: {len(all_hotel_offers)}")
            return all_hotel_offers
    
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
    
    def _process_hotel_results_with_fallback(self, hotel_list: List[Dict[str, Any]], 
                                           hotels_with_offers: List[Dict[str, Any]], 
                                           input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process hotel results, combining base hotel info with offers when available.
        Always return hotels, sorted by preference (hotels with offers first).
        """
        try:
            processed_hotels = []
            
            # Create a map of hotel IDs to offers for quick lookup
            offers_map = {}
            for hotel_offer in hotels_with_offers:
                hotel_info = hotel_offer.get("hotel", {})
                hotel_id = hotel_info.get("hotelId")
                if hotel_id:
                    offers_map[hotel_id] = hotel_offer
            
            # Process all hotels from the original search
            for hotel_data in hotel_list[:input_data.get("max_results", 20)]:
                try:
                    hotel_id = hotel_data.get("hotelId")
                    hotel_name = hotel_data.get("name", "Unknown Hotel")
                    
                    # Check if this hotel has offers
                    hotel_with_offers = offers_map.get(hotel_id)
                    
                    if hotel_with_offers:
                        # Use the hotel data with offers (full processing)
                        hotel_info = hotel_with_offers.get("hotel", {})
                        offers_data = hotel_with_offers.get("offers", [])
                        
                        # Process amenities from offers data
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
                        
                        # Create hotel with offers
                        hotel = Hotel(
                            hotel_id=hotel_id,
                            chain_code=hotel_info.get("chainCode"),
                            name=hotel_info.get("name", hotel_name),
                            rating=hotel_info.get("rating"),
                            address=hotel_info.get("address", {}),
                            contact=hotel_info.get("contact", {}),
                            description=hotel_info.get("description", {}).get("text"),
                            amenities=amenities,
                            media=hotel_info.get("media", []),
                            offers=processed_offers
                        )
                        
                    else:
                        # Create hotel without offers (basic info only)
                        hotel = Hotel(
                            hotel_id=hotel_id,
                            chain_code=hotel_data.get("chainCode"),
                            name=hotel_name,
                            rating=None,  # Not available in basic search
                            address={"countryCode": hotel_data.get("address", {}).get("countryCode", "")},
                            contact={},
                            description=None,
                            amenities=[],
                            media=[],
                            offers=[]  # No offers available
                        )
                    
                    processed_hotels.append(hotel)
                    
                except Exception as e:
                    self.log(f"Error processing hotel {hotel_data.get('hotelId', 'unknown')}: {e}")
                    continue
            
            # Sort hotels: those with offers first, then by name
            processed_hotels.sort(key=lambda h: (len(h.offers) == 0, h.name))
            
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
                    "hotels_with_offers": len([h for h in processed_hotels if h.offers]),
                    "hotels_without_offers": len([h for h in processed_hotels if not h.offers]),
                    "search_radius": input_data.get("radius", 20),
                    "currency": input_data.get("currency", "USD"),
                    "sorting": "offers_first"
                }
            )
            
            hotels_with_offers_count = result.meta["hotels_with_offers"]
            hotels_without_offers_count = result.meta["hotels_without_offers"]
            
            self.log(f"🏨 Processed {len(processed_hotels)} hotels: "
                    f"{hotels_with_offers_count} with offers, "
                    f"{hotels_without_offers_count} without offers")
            
            return result.model_dump()
            
        except Exception as e:
            raise Exception(f"Error processing hotel results with fallback: {e}")
    
    def _generate_no_hotels_message(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return clear message when no hotels are available"""
        
        no_hotels_result = HotelSearchResult(
            hotels=[],  # Empty list - no hotels
            search_criteria={
                "cityCode": input_data.get("cityCode", "Unknown"),
                "checkInDate": input_data.get("checkInDate", ""),
                "checkOutDate": input_data.get("checkOutDate", ""),
                "adults": input_data.get("adults", 1),
                "children": input_data.get("children", 0),
                "rooms": input_data.get("rooms", 1)
            },
            meta={
                "count": 0,
                "message": "No hotels available for this destination",
                "status": "no_results",
                "data_source": "amadeus_api",
                "search_attempted": True
            }
        )
        
        self.log("❌ No hotels available - returning empty results with clear message")
        return self.format_output(no_hotels_result.model_dump())
