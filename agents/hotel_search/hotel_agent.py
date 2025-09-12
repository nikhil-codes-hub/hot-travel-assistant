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
            
            # Get offers for the hotels (this will return consolidated results)
            hotels_with_offers = await self._get_hotel_offers(hotel_list, input_data)
            
            # Combine hotel list data with offers data, ensuring all hotels are shown
            combined_hotels = await self._combine_hotels_with_offers(hotel_list, hotels_with_offers)
            
            # Process and format results (now includes hotels without offers)
            result = self._process_hotel_results(combined_hotels, input_data)
            
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
    
    async def _get_city_coordinates(self, flight_city_code: str) -> tuple:
        """Get coordinates for cities using LLM intelligence instead of hardcoded mappings"""
        try:
            # Try to get coordinates from LLM first
            coordinates = await self._get_coordinates_from_llm(flight_city_code)
            if coordinates:
                return coordinates
        except Exception as e:
            self.log(f"⚠️ LLM coordinate lookup failed: {e}")
        
        # Fallback to basic hardcoded coordinates for major cities only
        fallback_coordinates = {
            "PAR": (48.8566, 2.3522),     # Paris
            "LON": (51.5074, -0.1278),    # London  
            "NYC": (40.7128, -74.0060),   # New York
            "BKK": (13.7563, 100.5018),   # Bangkok
            "BLR": (12.9716, 77.5946),    # Bangalore/Bengaluru
            "MYSORE": (12.2958, 76.6394), # Mysore, Karnataka
            "RAJASTHAN": (27.0238, 74.2179), # Jaipur, Rajasthan  
            "VIENNA": (48.2082, 16.3738), # Vienna, Austria
            "MATHURA": (27.4924, 77.6737), # Mathura, Uttar Pradesh
        }
        
        return fallback_coordinates.get(flight_city_code, (48.8566, 2.3522))  # Default to Paris
    
    async def _get_coordinates_from_llm(self, city_code: str) -> tuple:
        """Use LLM to get coordinates for any city dynamically"""
        try:
            from google.cloud import aiplatform
            from vertexai.generative_models import GenerativeModel
            
            # Initialize Vertex AI if not already done
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            
            if not project_id:
                return None
                
            try:
                aiplatform.init(project=project_id, location=location)
            except:
                pass  # May already be initialized
            
            model = GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""
You are a geographic information assistant. Given a city code or city name, provide the exact latitude and longitude coordinates.

City code: {city_code}

Common mappings:
- BKK = Bangkok, Thailand
- BLR = Bangalore/Bengaluru, India  
- PAR = Paris, France
- LON = London, UK
- NYC = New York City, USA
- TYO = Tokyo, Japan
- DXB = Dubai, UAE
- SIN = Singapore
- SYD = Sydney, Australia
- ZUR = Zurich, Switzerland
- MYSORE = Mysore, Karnataka, India
- RAJASTHAN = Jaipur, Rajasthan, India (capital city)
- VIENNA = Vienna, Austria  
- MATHURA = Mathura, Uttar Pradesh, India

IMPORTANT: Return ONLY the coordinates in this exact format: "latitude,longitude"
Example: "12.9716,77.5946"

Do not include any other text, explanations, or formatting. Just the coordinates.
"""
            
            response = await model.generate_content_async(prompt)
            
            # Parse response to extract coordinates
            coords_text = response.text.strip()
            if ',' in coords_text:
                lat_str, lng_str = coords_text.split(',')
                lat = float(lat_str.strip())
                lng = float(lng_str.strip())
                
                self.log(f"🗺️ LLM coordinates for {city_code}: ({lat}, {lng})")
                return (lat, lng)
                
        except Exception as e:
            self.log(f"❌ LLM coordinate extraction failed for {city_code}: {e}")
            return None
        
        return None
    
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
                "cityCode": original_city_code,
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
                f"{self.amadeus_base_url}/v1/reference-data/locations/hotels/by-city",
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
        """Get hotel offers for specific hotels by searching each hotel individually"""
        if not hotels:
            return []
        
        # Take first 10 hotels to avoid too many API calls
        hotel_ids = [hotel["hotelId"] for hotel in hotels[:10]]
        
        all_offers = []
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Iterate through each hotel ID individually
            for hotel_id in hotel_ids:
                try:
                    # Build query parameters for individual hotel
                    params = {
                        "hotelIds": hotel_id,  # Single hotel ID, not comma-separated
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
                    
                    self.log(f"🔍 Searching hotel offers for hotel ID: {hotel_id}")
                    
                    response = await client.get(
                        f"{self.amadeus_base_url}/v3/shopping/hotel-offers",
                        params=params,
                        headers=headers,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    
                    offers_response = response.json()
                    hotel_offers = offers_response.get("data", [])
                    
                    if hotel_offers:
                        all_offers.extend(hotel_offers)
                        self.log(f"✅ Found {len(hotel_offers)} offers for hotel {hotel_id}")
                    else:
                        self.log(f"⚠️  No offers available for hotel {hotel_id}")
                        
                except Exception as e:
                    self.log(f"❌ Error searching hotel {hotel_id}: {str(e)}")
                    continue  # Continue with next hotel if one fails
            
            self.log(f"📊 Total consolidated offers: {len(all_offers)} from {len(hotel_ids)} hotels searched")
            return all_offers
    
    async def _combine_hotels_with_offers(self, hotel_list: List[Dict[str, Any]], hotels_with_offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine hotel list with offers, showing all hotels and sorting those with offers first"""
        
        # Create a mapping of hotel ID to offers data
        offers_by_hotel_id = {}
        for hotel_offer_data in hotels_with_offers:
            hotel_info = hotel_offer_data.get("hotel", {})
            hotel_id = hotel_info.get("hotelId")
            if hotel_id:
                offers_by_hotel_id[hotel_id] = hotel_offer_data
        
        combined_hotels = []
        hotels_with_offers_list = []
        hotels_without_offers_list = []
        
        # Process all hotels from the original hotel list
        for hotel in hotel_list:
            hotel_id = hotel.get("hotelId")
            
            if hotel_id in offers_by_hotel_id:
                # Hotel has offers - use the data with offers
                hotels_with_offers_list.append(offers_by_hotel_id[hotel_id])
                self.log(f"✅ Hotel {hotel.get('name', hotel_id)} has offers available")
            else:
                # Hotel has no offers - create structure without offers
                hotel_without_offers = {
                    "hotel": hotel,
                    "offers": []  # Empty offers array
                }
                hotels_without_offers_list.append(hotel_without_offers)
        
        # Sort: Hotels with offers first, then hotels without offers
        combined_hotels = hotels_with_offers_list + hotels_without_offers_list
        
        self.log(f"🏨 Combined results: {len(hotels_with_offers_list)} hotels with offers, {len(hotels_without_offers_list)} hotels without offers")
        
        return combined_hotels
    
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
                    
                    # Process offers (may be empty for hotels without availability)
                    processed_offers = []
                    if offers_data:
                        self.log(f"🏨 Processing {len(offers_data)} offers for {hotel_info.get('name', 'Unknown Hotel')}")
                    else:
                        self.log(f"📋 Hotel {hotel_info.get('name', 'Unknown Hotel')} listed without offers (no availability for dates)")
                    
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
        """Generate fallback hotel data for cities when Amadeus API is unavailable"""
        city_code = input_data.get("cityCode", "").upper()
        check_in = input_data["checkInDate"]
        check_out = input_data["checkOutDate"]
        adults = input_data["adults"]
        rooms = input_data.get("rooms", 1)
        
        # Define hotel data for requested cities
        city_hotels = {
            "MYSORE": [
                {
                    "hotel_id": "MYS001",
                    "name": "The Windflower Resort & Spa Mysore",
                    "rating": 4.5,
                    "address": {"lines": ["Mysore-Ooty Road"], "cityName": "Mysore"},
                    "price": {"currency": "USD", "total": "120"},
                    "room_type": "DELUXE_ROOM",
                    "amenities": [
                        {"description": "Palace Views"},
                        {"description": "Spa & Wellness"},
                        {"description": "Traditional Architecture"}
                    ]
                },
                {
                    "hotel_id": "MYS002", 
                    "name": "Royal Orchid Metropole",
                    "rating": 4,
                    "address": {"lines": ["5 Jhansi Lakshmi Bai Road"], "cityName": "Mysore"},
                    "price": {"currency": "USD", "total": "95"},
                    "room_type": "PREMIUM_ROOM",
                    "amenities": [
                        {"description": "Heritage Hotel"},
                        {"description": "Swimming Pool"},
                        {"description": "Multi-cuisine Restaurant"}
                    ]
                },
                {
                    "hotel_id": "MYS003",
                    "name": "Hotel Maurya Residency",
                    "rating": 3.5,
                    "address": {"lines": ["2919/1 Vinoba Road"], "cityName": "Mysore"},
                    "price": {"currency": "USD", "total": "75"},
                    "room_type": "STANDARD_ROOM",
                    "amenities": [
                        {"description": "City Center Location"},
                        {"description": "Business Center"},
                        {"description": "Complimentary WiFi"}
                    ]
                }
            ],
            "RAJASTHAN": [
                {
                    "hotel_id": "RAJ001",
                    "name": "The Oberoi Udaivilas, Udaipur",
                    "rating": 5,
                    "address": {"lines": ["Haridasji ki Magri"], "cityName": "Udaipur"},
                    "price": {"currency": "USD", "total": "450"},
                    "room_type": "LUXURY_SUITE",
                    "amenities": [
                        {"description": "Lake Palace Views"},
                        {"description": "Royal Spa"},
                        {"description": "Fine Dining"}
                    ]
                },
                {
                    "hotel_id": "RAJ002",
                    "name": "Rambagh Palace, Jaipur",
                    "rating": 5,
                    "address": {"lines": ["Bhawani Singh Road"], "cityName": "Jaipur"},
                    "price": {"currency": "USD", "total": "380"},
                    "room_type": "PALACE_SUITE",
                    "amenities": [
                        {"description": "Former Royal Palace"},
                        {"description": "Marble Spa"},
                        {"description": "Polo Bar"}
                    ]
                },
                {
                    "hotel_id": "RAJ003",
                    "name": "Suryagarh Jaisalmer",
                    "rating": 4.5,
                    "address": {"lines": ["Kagga Road"], "cityName": "Jaisalmer"},
                    "price": {"currency": "USD", "total": "320"},
                    "room_type": "DESERT_SUITE",
                    "amenities": [
                        {"description": "Desert Views"},
                        {"description": "Traditional Architecture"},
                        {"description": "Cultural Experiences"}
                    ]
                }
            ],
            "VIENNA": [
                {
                    "hotel_id": "VIE001",
                    "name": "Hotel Sacher Vienna",
                    "rating": 5,
                    "address": {"lines": ["Philharmoniker Strasse 4"], "cityName": "Vienna"},
                    "price": {"currency": "USD", "total": "520"},
                    "room_type": "LUXURY_SUITE",
                    "amenities": [
                        {"description": "Historic Luxury"},
                        {"description": "Original Sachertorte"},
                        {"description": "Opera House Views"}
                    ]
                },
                {
                    "hotel_id": "VIE002",
                    "name": "The Ritz-Carlton, Vienna",
                    "rating": 5,
                    "address": {"lines": ["Schubertring 5-7"], "cityName": "Vienna"},
                    "price": {"currency": "USD", "total": "480"},
                    "room_type": "CLUB_ROOM",
                    "amenities": [
                        {"description": "Ringstrasse Location"},
                        {"description": "Luxury Spa"},
                        {"description": "Rooftop Dining"}
                    ]
                },
                {
                    "hotel_id": "VIE003",
                    "name": "Hotel Imperial Vienna",
                    "rating": 5,
                    "address": {"lines": ["Kärntner Ring 16"], "cityName": "Vienna"},
                    "price": {"currency": "USD", "total": "420"},
                    "room_type": "IMPERIAL_ROOM",
                    "amenities": [
                        {"description": "Imperial Palace Style"},
                        {"description": "Fine Austrian Cuisine"},
                        {"description": "Historic Elegance"}
                    ]
                }
            ],
            "MATHURA": [
                {
                    "hotel_id": "MTU001",
                    "name": "The Radha Ashok",
                    "rating": 4,
                    "address": {"lines": ["Masani Road"], "cityName": "Mathura"},
                    "price": {"currency": "USD", "total": "85"},
                    "room_type": "DELUXE_ROOM",
                    "amenities": [
                        {"description": "Temple City Location"},
                        {"description": "Vegetarian Restaurant"},
                        {"description": "Krishna Temple Views"}
                    ]
                },
                {
                    "hotel_id": "MTU002",
                    "name": "Hotel Brij Raj",
                    "rating": 3.5,
                    "address": {"lines": ["Krishna Nagar"], "cityName": "Mathura"},
                    "price": {"currency": "USD", "total": "65"},
                    "room_type": "STANDARD_ROOM", 
                    "amenities": [
                        {"description": "Pilgrimage Center"},
                        {"description": "Traditional Hospitality"},
                        {"description": "Yamuna River Proximity"}
                    ]
                },
                {
                    "hotel_id": "MTU003",
                    "name": "Shri Radha Brij Vasundhara Resort & Spa",
                    "rating": 4,
                    "address": {"lines": ["NH-2, Govardhan Road"], "cityName": "Mathura"},
                    "price": {"currency": "USD", "total": "110"},
                    "room_type": "RESORT_ROOM",
                    "amenities": [
                        {"description": "Spiritual Retreat"},
                        {"description": "Ayurvedic Spa"},
                        {"description": "Cultural Programs"}
                    ]
                }
            ]
        }
        
        # Get hotels for the specified city or default to generic hotels
        selected_hotels = city_hotels.get(city_code, [
            {
                "hotel_id": "DEFAULT001",
                "name": f"Premium Hotel in {city_code}",
                "rating": 4,
                "address": {"lines": ["City Center"], "cityName": city_code},
                "price": {"currency": "USD", "total": "150"},
                "room_type": "DELUXE_ROOM",
                "amenities": [
                    {"description": "Modern Amenities"},
                    {"description": "Business Center"},
                    {"description": "Fitness Center"}
                ]
            }
        ])
        
        # Create formatted hotel offers
        processed_hotels = []
        for idx, hotel_data in enumerate(selected_hotels):
            hotel = {
                "hotel_id": hotel_data["hotel_id"],
                "name": hotel_data["name"],
                "rating": hotel_data["rating"],
                "address": hotel_data["address"],
                "contact": {},
                "description": f"Excellent accommodation in {hotel_data['address']['cityName']}",
                "amenities": hotel_data["amenities"],
                "media": [],
                "offers": [{
                    "id": f"offer_{idx}_{hotel_data['hotel_id']}",
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "room_quantity": rooms,
                    "price": hotel_data["price"],
                    "room": {"type": hotel_data["room_type"]},
                    "guests": {"adults": adults},
                    "policies": {}
                }]
            }
            processed_hotels.append(hotel)
        
        result = {
            "hotels": processed_hotels,
            "search_criteria": {
                "cityCode": city_code,
                "checkInDate": check_in,
                "checkOutDate": check_out,
                "adults": adults,
                "children": input_data.get("children", 0),
                "rooms": rooms
            },
            "meta": {
                "count": len(processed_hotels),
                "search_radius": input_data.get("radius", 20),
                "currency": input_data.get("currency", "USD"),
                "data_source": "fallback_hotels",
                "is_fallback": True
            }
        }
        
        self.log(f"🏨 Generated {len(processed_hotels)} fallback hotels for {city_code}")
        return self.format_output(result)