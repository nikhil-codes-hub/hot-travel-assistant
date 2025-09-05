"""
Amadeus Location Service for dynamic city/airport code lookup
Used to get accurate location codes for events instead of hardcoded mappings
"""

import os
import httpx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import structlog

logger = structlog.get_logger()

class AmadeusLocationService:
    def __init__(self):
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.amadeus_base_url = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
        self.access_token = None
        self.token_expires_at = None
        self._location_cache = {}  # Cache for location lookups
    
    async def get_city_and_airport_codes(self, location_name: str, country: str = None) -> Dict[str, str]:
        """
        Get both city and airport codes for a location using Amadeus APIs
        
        Args:
            location_name: Name of the city/location
            country: Country name or code (optional, helps with accuracy)
            
        Returns:
            Dict with 'city_code', 'airport_code', 'city_name', 'country_code'
        """
        # Check cache first
        cache_key = f"{location_name.lower()}_{country.lower() if country else ''}"
        if cache_key in self._location_cache:
            logger.info(f"🎯 Location cache hit for {location_name}")
            return self._location_cache[cache_key]
        
        # Check if Amadeus API is available
        if not self.amadeus_client_id or not self.amadeus_client_secret:
            logger.warning("⚠️ Amadeus API credentials not configured - using fallback mapping")
            return self._get_fallback_codes(location_name, country)
        
        try:
            await self._ensure_access_token()
            
            # Try to get both city and airport information
            location_data = await self._search_city_location(location_name, country)
            
            if location_data:
                result = {
                    "city_code": location_data.get("iataCode", ""),
                    "airport_code": location_data.get("iataCode", ""), 
                    "city_name": location_data.get("name", location_name),
                    "country_code": location_data.get("address", {}).get("countryCode", "")
                }
                
                # If we got a city result, try to find the main airport
                if result["city_code"]:
                    airport_data = await self._search_nearest_airport(location_name, country)
                    if airport_data:
                        result["airport_code"] = airport_data.get("iataCode", result["city_code"])
                
                # Cache the result
                self._location_cache[cache_key] = result
                
                logger.info(f"✅ Amadeus Location: {location_name} -> City: {result['city_code']}, Airport: {result['airport_code']}")
                return result
            
        except Exception as e:
            logger.error(f"❌ Amadeus Location Service error: {e}")
        
        # Fallback to hardcoded mapping
        fallback_result = self._get_fallback_codes(location_name, country)
        self._location_cache[cache_key] = fallback_result
        return fallback_result
    
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
    
    async def _search_city_location(self, location_name: str, country: str = None) -> Optional[Dict]:
        """Search for city using Amadeus City & Airport Search API"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "subType": ["CITY", "AIRPORT"],
                "keyword": location_name,
                "page[limit]": 10
            }
            
            # Add country filter if provided
            if country:
                params["countryCode"] = self._normalize_country_code(country)
            
            response = await client.get(
                f"{self.amadeus_base_url}/v1/reference-data/locations",
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                locations = data.get("data", [])
                
                # Prioritize exact matches and cities over airports
                for location in locations:
                    if (location.get("subType") == "CITY" and 
                        location_name.lower() in location.get("name", "").lower()):
                        return location
                
                # Return first result if no exact city match
                if locations:
                    return locations[0]
                    
            return None
    
    async def _search_nearest_airport(self, location_name: str, country: str = None) -> Optional[Dict]:
        """Search for nearest airport using Amadeus API"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "subType": "AIRPORT",
                "keyword": location_name,
                "page[limit]": 5
            }
            
            if country:
                params["countryCode"] = self._normalize_country_code(country)
            
            response = await client.get(
                f"{self.amadeus_base_url}/v1/reference-data/locations",
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                airports = data.get("data", [])
                
                # Return the first airport result
                if airports:
                    return airports[0]
                    
            return None
    
    def _normalize_country_code(self, country: str) -> str:
        """Convert country names to ISO country codes"""
        country_mapping = {
            "thailand": "TH",
            "united states": "US", 
            "usa": "US",
            "united kingdom": "GB",
            "uk": "GB",
            "france": "FR",
            "germany": "DE",
            "japan": "JP",
            "singapore": "SG",
            "australia": "AU",
            "canada": "CA",
            "india": "IN",
            "china": "CN",
            "italy": "IT",
            "spain": "ES",
            "switzerland": "CH"
        }
        
        country_lower = country.lower()
        return country_mapping.get(country_lower, country.upper()[:2])
    
    def _get_fallback_codes(self, location_name: str, country: str = None) -> Dict[str, str]:
        """Fallback hardcoded mapping when API is unavailable"""
        # Enhanced fallback mapping including event-specific locations
        location_mapping = {
            # Major cities
            "bangkok": {"city_code": "BKK", "airport_code": "BKK", "country_code": "TH"},
            "thailand": {"city_code": "BKK", "airport_code": "BKK", "country_code": "TH"},
            "chiang mai": {"city_code": "CNX", "airport_code": "CNX", "country_code": "TH"},
            "pattaya": {"city_code": "BKK", "airport_code": "BKK", "country_code": "TH"},  # Use Bangkok airport
            "phuket": {"city_code": "HKT", "airport_code": "HKT", "country_code": "TH"},
            
            # Water Lantern Festival locations
            "yi peng": {"city_code": "CNX", "airport_code": "CNX", "country_code": "TH"},  # Chiang Mai
            "loy krathong": {"city_code": "BKK", "airport_code": "BKK", "country_code": "TH"},  # Multiple locations, default Bangkok
            
            # Other major destinations
            "paris": {"city_code": "PAR", "airport_code": "CDG", "country_code": "FR"},
            "london": {"city_code": "LON", "airport_code": "LHR", "country_code": "GB"},
            "new york": {"city_code": "NYC", "airport_code": "JFK", "country_code": "US"},
            "tokyo": {"city_code": "TYO", "airport_code": "NRT", "country_code": "JP"},
            "singapore": {"city_code": "SIN", "airport_code": "SIN", "country_code": "SG"},
            "dubai": {"city_code": "DXB", "airport_code": "DXB", "country_code": "AE"},
            "mumbai": {"city_code": "BOM", "airport_code": "BOM", "country_code": "IN"},
            "sydney": {"city_code": "SYD", "airport_code": "SYD", "country_code": "AU"},
            "los angeles": {"city_code": "LAX", "airport_code": "LAX", "country_code": "US"},
            
            # Festival and event specific locations
            "oktoberfest": {"city_code": "MUC", "airport_code": "MUC", "country_code": "DE"},  # Munich
            "munich": {"city_code": "MUC", "airport_code": "MUC", "country_code": "DE"},
            "carnival": {"city_code": "RIO", "airport_code": "GIG", "country_code": "BR"},  # Rio de Janeiro
            "rio de janeiro": {"city_code": "RIO", "airport_code": "GIG", "country_code": "BR"},
        }
        
        location_lower = location_name.lower()
        
        # Check direct mapping
        if location_lower in location_mapping:
            result = location_mapping[location_lower].copy()
            result["city_name"] = location_name
            logger.info(f"📍 Fallback mapping: {location_name} -> {result}")
            return result
        
        # Check partial matches
        for mapped_location, codes in location_mapping.items():
            if mapped_location in location_lower or location_lower in mapped_location:
                result = codes.copy()
                result["city_name"] = location_name
                logger.info(f"📍 Fallback partial match: {location_name} -> {result}")
                return result
        
        # Ultimate fallback - use Bangkok for Thailand-related queries, Paris otherwise
        if country and "th" in country.lower():
            default_result = {"city_code": "BKK", "airport_code": "BKK", "country_code": "TH", "city_name": location_name}
        else:
            default_result = {"city_code": "PAR", "airport_code": "CDG", "country_code": "FR", "city_name": location_name}
        
        logger.warning(f"⚠️ Using default fallback for {location_name}: {default_result}")
        return default_result