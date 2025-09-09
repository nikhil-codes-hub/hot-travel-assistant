import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent
from agents.image_search.image_search_agent import ImageSearchAgent

class ItineraryDay(BaseModel):
    day: int = Field(..., description="Day number")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    location: str = Field(..., description="Location/city for this day")
    activities: List[str] = Field(..., description="Planned activities")
    accommodation: Optional[Dict[str, Any]] = Field(None, description="Hotel details")
    transportation: Optional[Dict[str, Any]] = Field(None, description="Flight/transport details")
    meals: List[str] = Field([], description="Meal recommendations")
    budget_estimate: Optional[float] = Field(None, description="Daily budget estimate")

class TravelReadinessItem(BaseModel):
    category: str = Field(..., description="Category: documents/health/insurance/logistics")
    item: str = Field(..., description="Specific requirement")
    status: str = Field(..., description="required/recommended/optional")
    deadline: Optional[str] = Field(None, description="Deadline for completion")
    details: str = Field(..., description="Additional details")

class Itinerary(BaseModel):
    title: str = Field("Travel Itinerary", description="Itinerary title")
    destination: str = Field("Unknown", description="Primary destination")
    destination_info: Optional[Dict[str, Any]] = Field(None, description="Destination details and information")
    duration: int = Field(7, description="Trip duration in days")
    traveler_count: int = Field(1, description="Number of travelers")
    departure_date: str = Field("TBD", description="Departure date")
    return_date: str = Field("TBD", description="Return date")
    
    # Trip components
    days: List[ItineraryDay] = Field([], description="Day-by-day itinerary")
    flights: List[Dict[str, Any]] = Field([], description="Flight details")
    accommodations: List[Dict[str, Any]] = Field([], description="Hotel details")
    total_cost: Dict[str, Any] = Field({"currency": "USD", "total": 0}, description="Total trip cost breakdown")
    
    # Visual content
    hero_images: List[Dict[str, Any]] = Field([], description="Main showcase images for itinerary overview")
    gallery_images: List[Dict[str, Any]] = Field([], description="Additional destination and event images")
    
    # Travel readiness
    travel_readiness: List[TravelReadinessItem] = Field([], description="Travel preparation checklist")
    
    # Rationale and insights
    rationale: str = Field("Itinerary pending detailed requirements", description="Why this itinerary works")
    highlights: List[str] = Field([], description="Trip highlights")
    tips: List[str] = Field([], description="Travel tips")

class PrepareItineraryResult(BaseModel):
    itinerary: Itinerary
    confidence_score: float = Field(..., description="Confidence in itinerary quality")
    personalization_applied: bool = Field(..., description="Whether customer profile was considered")
    next_steps: List[str] = Field(..., description="Next steps for booking")

class PrepareItineraryAgent(BaseAgent):
    def __init__(self):
        super().__init__("PrepareItineraryAgent")
        self.ai_provider = "vertex"  # Only using Vertex AI
        self.ai_available = False
        
        # Initialize Image Search Agent
        self.image_agent = ImageSearchAgent()
        
        try:
            self.log("🔧 [Itinerary Agent] Initializing Vertex AI")
            
            # Initialize Vertex AI
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            
            if not project_id:
                self.log("❌ [Itinerary Agent] GOOGLE_CLOUD_PROJECT not set - Vertex AI unavailable")
                self.log("💡 [Itinerary Agent] Please set GOOGLE_CLOUD_PROJECT in your .env file")
            else:
                self.log(f"🔄 [Itinerary Agent] Connecting to Vertex AI: project={project_id}, location={location}")
                aiplatform.init(project=project_id, location=location)
                self.model = None  # Will use aiplatform.gapic.PredictionServiceClient
                self.ai_available = True
                self.log("✅ [Itinerary Agent] Vertex AI successfully initialized")
                    
        except Exception as e:
            self.log(f"❌ [Itinerary Agent] Vertex AI initialization failed: {str(e)}")
            self.log("⚠️  [Itinerary Agent] Falling back to template-based itinerary generation")
            self.ai_available = False
            self.model = None
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Assemble a coherent travel itinerary from search results
        
        Input:
        - requirements: Extracted travel requirements
        - customer_profile: Customer profile and preferences
        - flight_offers: Enhanced flight offers from OffersAgent
        - hotel_offers: Enhanced hotel offers from OffersAgent
        - destination_suggestions: From DestinationDiscoveryAgent (if applicable)
        - compliance_data: Visa/health requirements (if available)
        """
        
        required_fields = ["requirements"]
        self.validate_input(input_data, required_fields)
        
        try:
            if self.ai_available:
                self.log("🤖 [Itinerary Agent] Using AI-powered itinerary generation")
                result = await self._create_ai_itinerary(input_data)
            else:
                self.log("📋 [Itinerary Agent] AI unavailable - using template-based itinerary generation")
                result = await self._create_rule_based_itinerary(input_data)
            
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"❌ [Itinerary Agent] Error during itinerary generation: {e}")
            self.log("🔄 [Itinerary Agent] Falling back to emergency itinerary generation")
            return await self._generate_fallback_itinerary(input_data)
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-2.0-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    
    def _clean_ai_data(self, ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean AI response data to handle string values that should be dictionaries"""
        try:
            self.log(f"🔍 Cleaning AI data structure...")
            # Log the original structure for debugging
            if "travel_components" in ai_data:
                tc = ai_data["travel_components"]
                if "flights" in tc:
                    self.log(f"📡 Original flights type: {type(tc['flights'])}")
                if "hotels" in tc:
                    self.log(f"🏨 Original hotels type: {type(tc['hotels'])}")
            # Clean daily_plan items
            if "daily_plan" in ai_data and isinstance(ai_data["daily_plan"], list):
                for day_plan in ai_data["daily_plan"]:
                    if isinstance(day_plan, dict):
                        # Fix accommodation field
                        if "accommodation" in day_plan and isinstance(day_plan["accommodation"], str):
                            day_plan["accommodation"] = {
                                "description": day_plan["accommodation"],
                                "type": "accommodation"
                            }
                        
                        # Fix transportation field
                        if "transportation" in day_plan and isinstance(day_plan["transportation"], str):
                            day_plan["transportation"] = {
                                "description": day_plan["transportation"], 
                                "type": "transport"
                            }
            
            # Clean travel_components
            if "travel_components" in ai_data and isinstance(ai_data["travel_components"], dict):
                travel_components = ai_data["travel_components"]
                
                # Fix flights field - handle both string and list with string elements
                if "flights" in travel_components:
                    flights = travel_components["flights"]
                    if isinstance(flights, str):
                        travel_components["flights"] = [{
                            "description": flights,
                            "type": "flight_summary"
                        }]
                    elif isinstance(flights, list):
                        cleaned_flights = []
                        for flight in flights:
                            if isinstance(flight, str):
                                cleaned_flights.append({
                                    "description": flight,
                                    "type": "flight_summary"
                                })
                            elif isinstance(flight, dict):
                                cleaned_flights.append(flight)
                        travel_components["flights"] = cleaned_flights
                
                # Fix hotels field - handle both string and list with string elements
                if "hotels" in travel_components:
                    hotels = travel_components["hotels"]
                    if isinstance(hotels, str):
                        travel_components["hotels"] = [{
                            "description": hotels,
                            "type": "accommodation_summary"
                        }]
                    elif isinstance(hotels, list):
                        cleaned_hotels = []
                        for hotel in hotels:
                            if isinstance(hotel, str):
                                cleaned_hotels.append({
                                    "description": hotel,
                                    "type": "accommodation_summary"
                                })
                            elif isinstance(hotel, dict):
                                cleaned_hotels.append(hotel)
                        travel_components["hotels"] = cleaned_hotels
            
            return ai_data
            
        except Exception as e:
            self.log(f"Error cleaning AI data: {e}")
            return ai_data
    
    async def _create_ai_itinerary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create itinerary using AI for coherent planning"""
        
        prompt = self._create_itinerary_prompt(input_data)
        
        # Call AI API
        if self.ai_provider == "vertex":
            response = await self._call_vertex_ai(prompt)
        else:
            response = self.model.generate_content(prompt)
        
        try:
            # Parse AI response
            if self.ai_provider == "vertex":
                response_text = response.strip()
            else:
                response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            ai_data = json.loads(response_text)
            
            # Clean AI data to handle string values that should be dicts
            ai_data = self._clean_ai_data(ai_data)
            
            # Build structured itinerary
            result = self._build_structured_itinerary(ai_data, input_data)
            return result.model_dump()
            
        except Exception as e:
            self.log(f"AI parsing error: {e}")
            return await self._create_rule_based_itinerary(input_data)
    
    def _create_itinerary_prompt(self, input_data: Dict[str, Any]) -> str:
        """Create AI prompt for itinerary generation"""
        
        requirements = input_data.get("requirements", {})
        customer_profile = input_data.get("customer_profile", {})
        flight_offers = input_data.get("flight_offers", [])
        hotel_offers = input_data.get("hotel_offers", [])
        event_details = input_data.get("event_details", {})
        
        # Extract key information
        destination = requirements.get("destination", "Selected destination")
        duration = requirements.get("duration", 7)
        budget = requirements.get("budget")
        passengers = requirements.get("passengers", 1)
        departure_date = requirements.get("departure_date", "2024-06-01")
        
        # Customer context
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        travel_history = customer_profile.get("travel_history", [])
        preferences = customer_profile.get("preferences", {})
        
        # Event context if available
        event_context = ""
        if event_details:
            event_name = event_details.get("name", "")
            event_description = event_details.get("description", "")
            event_context = f"\n\nSPECIAL EVENT: {event_name}\n{event_description}\nInclude this event in the itinerary highlights and plan activities around it."
        
        return f"""
Create a detailed travel itinerary for this trip. Be specific and practical.

TRIP REQUIREMENTS:
- Destination: {destination}
- Duration: {duration} days
- Travelers: {passengers}
- Departure: {departure_date}
- Budget: {budget or "Not specified"}{event_context}

CUSTOMER PROFILE:
- Loyalty tier: {loyalty_tier}
- Previous trips: {len(travel_history)} recorded trips
- Preferences: {preferences}

AVAILABLE OFFERS:
- Flight options: {len(flight_offers)} available
- Hotel options: {len(hotel_offers)} available

Create a comprehensive itinerary and return ONLY valid JSON:
{{
    "itinerary_overview": {{
        "title": "Descriptive trip title",
        "destination": "{destination}",
        "destination_info": {{
            "description": "Brief compelling description of the destination (2-3 sentences)",
            "best_time_to_visit": "Season/month information for the travel dates",
            "local_culture": "Key cultural highlights or customs to know",
            "currency": "Local currency and approximate exchange rate",
            "language": "Primary language(s) spoken",
            "timezone": "Timezone information relative to traveler's origin",
            "popular_attractions": ["Top 5-7 must-see attractions and landmarks in {destination}"],
            "event_highlights": "Special event information and related activities if applicable"
        }},
        "duration": {duration},
        "travelers": {passengers},
        "departure_date": "{departure_date}",
        "return_date": "calculated return date",
        "total_budget_estimate": "estimated total cost in USD"
    }},
    "daily_plan": [
        {{
            "day": 1,
            "date": "YYYY-MM-DD",
            "location": "City/Area",
            "activities": ["Arrival", "Hotel check-in", "Explore area"],
            "meals": ["Lunch at local restaurant", "Dinner recommendation"],
            "accommodation": "Hotel info if relevant",
            "budget_estimate": 200
        }}
    ],
    "travel_components": {{
        "flights": ["Flight summary from offers"],
        "hotels": ["Hotel summary from offers"],
        "total_cost": {{
            "flights": 800,
            "hotels": 600,
            "activities": 400,
            "meals": 300,
            "total": 2100,
            "currency": "USD"
        }}
    }},
    "rationale": "Why this itinerary works for the traveler",
    "highlights": ["Key experiences including event highlights if applicable", "Must-see attractions and popular landmarks", "Unique opportunities and local experiences"],
    "travel_tips": ["Practical advice", "Local insights", "Money-saving tips"],
    "confidence_score": 0.0-1.0
}}

Focus on:
1. Realistic day-by-day planning
2. Logical flow and pacing
3. Budget considerations
4. Customer preferences alignment
5. Practical logistics (check-in times, travel times)
6. Include popular city attractions and landmarks
7. Incorporate event highlights and related activities if applicable
8. Provide local cultural experiences and must-see sights
"""
    
    def _build_structured_itinerary(self, ai_data: Dict[str, Any], input_data: Dict[str, Any]) -> PrepareItineraryResult:
        """Build structured itinerary from AI response"""
        
        overview = ai_data.get("itinerary_overview", {})
        daily_plans = ai_data.get("daily_plan", [])
        travel_components = ai_data.get("travel_components", {})
        
        # Build daily itinerary
        days = []
        for plan in daily_plans:
            day = ItineraryDay(
                day=plan.get("day", 1),
                date=plan.get("date", "2024-06-01"),
                location=plan.get("location", "Destination"),
                activities=plan.get("activities", []),
                accommodation=plan.get("accommodation"),
                transportation=plan.get("transportation"),
                meals=plan.get("meals", []),
                budget_estimate=plan.get("budget_estimate")
            )
            days.append(day)
        
        # Build travel readiness checklist
        requirements = input_data.get("requirements", {})
        travel_readiness = self._generate_travel_readiness(requirements)
        
        # Create main itinerary
        itinerary = Itinerary(
            title=overview.get("title", f"Trip to {requirements.get('destination', 'Destination')}"),
            destination=overview.get("destination", requirements.get("destination", "")),
            destination_info=overview.get("destination_info", self._get_default_destination_info(requirements.get("destination", ""))),
            duration=overview.get("duration", requirements.get("duration", 7)),
            traveler_count=overview.get("travelers", requirements.get("passengers", 1)),
            departure_date=overview.get("departure_date") or requirements.get("departure_date") or "TBD",
            return_date=overview.get("return_date") or requirements.get("return_date") or "TBD",
            days=days,
            flights=travel_components.get("flights", []),
            accommodations=travel_components.get("hotels", []),
            total_cost=travel_components.get("total_cost", {}),
            travel_readiness=travel_readiness,
            rationale=ai_data.get("rationale", "Itinerary planned based on requirements"),
            highlights=ai_data.get("highlights", []),
            tips=ai_data.get("travel_tips", [])
        )
        
        # Determine next steps
        next_steps = self._generate_next_steps(input_data)
        
        result = PrepareItineraryResult(
            itinerary=itinerary,
            confidence_score=ai_data.get("confidence_score", 0.7),
            personalization_applied=bool(input_data.get("customer_profile")),
            next_steps=next_steps
        )
        
        return result
    
    async def _create_rule_based_itinerary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced itinerary using rule-based logic with personalization"""
        
        requirements = input_data.get("requirements", {})
        customer_profile = input_data.get("customer_profile", {})
        flight_offers = input_data.get("flight_offers", [])
        hotel_offers = input_data.get("hotel_offers", [])
        destination_suggestions = input_data.get("destination_suggestions", [])
        event_details = input_data.get("event_details", {})
        
        duration = requirements.get("duration", 7)
        destination = requirements.get("destination", "Destination")
        departure_date = requirements.get("departure_date", "2024-06-01")
        budget = requirements.get("budget", 1000)
        passengers = requirements.get("passengers", 1)
        
        # Use destination suggestions if no specific destination
        if destination in ["somewhere snowy", "Destination"] and destination_suggestions:
            if isinstance(destination_suggestions, list) and destination_suggestions:
                destination = destination_suggestions[0].get("destination", destination)
            elif isinstance(destination_suggestions, dict) and destination_suggestions.get("suggestions"):
                destination = destination_suggestions["suggestions"][0].get("destination", destination)
        
        # Calculate return date
        try:
            dep_date = datetime.fromisoformat(departure_date)
            return_date = (dep_date + timedelta(days=duration-1)).isoformat()[:10]
        except:
            return_date = departure_date
        
        # Get customer preferences
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        preferences = customer_profile.get("preferences", {})
        preferred_cabin = preferences.get("preferred_cabin_class", "Economy")
        
        # Create enhanced daily plan with destination-specific activities
        days = []
        destination_activities = self._get_destination_activities(destination, duration)
        
        for i in range(duration):
            try:
                current_date = (datetime.fromisoformat(departure_date) + timedelta(days=i)).isoformat()[:10]
            except:
                current_date = departure_date
            
            # Get day-specific activities
            if i < len(destination_activities):
                activities = destination_activities[i]
            else:
                activities = ["Leisure day", "Explore local attractions", "Shopping and dining"]
            
            # Add transportation details for first and last day
            transportation = None
            if i == 0 and flight_offers:
                flight = flight_offers[0] if isinstance(flight_offers[0], dict) else {}
                transportation = {
                    "type": "flight_arrival",
                    "details": f"Arrival flight in {preferred_cabin} class",
                    "airline": flight.get("validatingAirlineCodes", [""])[0] if flight.get("validatingAirlineCodes") else "",
                    "estimated_cost": flight.get("price", {}).get("total", "TBD")
                }
            elif i == duration - 1 and flight_offers:
                transportation = {
                    "type": "flight_departure",
                    "details": f"Return flight in {preferred_cabin} class",
                    "estimated_cost": "Included in arrival flight"
                }
            
            # Add accommodation details
            accommodation = None
            if hotel_offers and i < duration - 1:  # No hotel on departure day
                hotel = hotel_offers[0] if isinstance(hotel_offers[0], dict) else {}
                accommodation = {
                    "type": "hotel",
                    "name": hotel.get("name", "Selected Hotel"),
                    "category": hotel.get("rating", "4-star") if isinstance(hotel.get("rating"), (int, float)) else "4-star",
                    "benefits": f"{loyalty_tier} member benefits apply" if loyalty_tier != "STANDARD" else "Standard booking"
                }
            
            # Enhanced meals based on destination and customer tier
            meals = self._get_destination_meals(destination, loyalty_tier)
            
            day = ItineraryDay(
                day=i + 1,
                date=current_date,
                location=destination,
                activities=activities,
                accommodation=accommodation,
                transportation=transportation,
                meals=meals,
                budget_estimate=budget / duration if budget else 150.0
            )
            days.append(day)
        
        # Enhanced cost calculation
        flight_cost = 0
        hotel_cost = 0
        
        if flight_offers and isinstance(flight_offers[0], dict):
            flight_price = flight_offers[0].get("price", {})
            if isinstance(flight_price, dict):
                flight_cost = float(flight_price.get("total", 800))
        
        if hotel_offers and isinstance(hotel_offers[0], dict):
            hotel_price = hotel_offers[0].get("offers", [{}])[0].get("price", {}) if hotel_offers[0].get("offers") else {}
            if isinstance(hotel_price, dict):
                hotel_cost = float(hotel_price.get("total", duration * 120))
        
        if flight_cost == 0:
            flight_cost = 800 * passengers
        if hotel_cost == 0:
            hotel_cost = duration * 120
        
        # Build enhanced travel readiness
        travel_readiness = self._generate_travel_readiness(requirements)
        
        # Create personalized highlights and tips
        highlights = self._get_destination_highlights(destination, event_details)
        tips = self._get_destination_tips(destination, loyalty_tier)
        
        # Enhanced rationale
        rationale = f"This {duration}-day itinerary for {destination} is curated for {passengers} travelers with {loyalty_tier} tier benefits. "
        if event_details:
            event_name = event_details.get("name", "special event")
            rationale += f"The itinerary includes {event_name} and related activities. "
        if destination_suggestions:
            rationale += f"Selected from recommended destinations based on your preference for snowy destinations. "
        rationale += f"The plan balances sightseeing, relaxation, and cultural experiences while maximizing your {loyalty_tier} member benefits."
        
        # Generate images for the itinerary
        hero_images, gallery_images = await self._generate_itinerary_images(
            destination, event_details, requirements
        )
        
        # Create itinerary
        itinerary = Itinerary(
            title=f"{duration}-Day Premium Trip to {destination}",
            destination=destination,
            destination_info=self._get_default_destination_info(destination),
            duration=duration,
            traveler_count=passengers,
            departure_date=departure_date,
            return_date=return_date,
            days=days,
            flights=flight_offers[:2] if flight_offers else [],
            accommodations=hotel_offers[:3] if hotel_offers else [],
            hero_images=hero_images,
            gallery_images=gallery_images,
            total_cost={
                "flights": flight_cost,
                "hotels": hotel_cost,
                "activities": duration * 75,
                "meals": duration * 90,
                "total": flight_cost + hotel_cost + (duration * 165),
                "currency": "USD",
                "savings_applied": f"{loyalty_tier} tier discounts included"
            },
            travel_readiness=travel_readiness,
            rationale=rationale,
            highlights=highlights,
            tips=tips
        )
        
        result = PrepareItineraryResult(
            itinerary=itinerary,
            confidence_score=0.85,  # Higher confidence with enhanced logic
            personalization_applied=True,
            next_steps=self._generate_next_steps(input_data)
        )
        
        return result.model_dump()
    
    def _get_destination_activities(self, destination: str, duration: int) -> List[List[str]]:
        """Get destination-specific activities for each day"""
        destination_lower = destination.lower()
        
        if any(keyword in destination_lower for keyword in ["zermatt", "switzerland", "swiss", "alpine"]):
            return [
                ["Arrival", "Airport/train transfer to Zermatt", "Hotel check-in", "Evening stroll through car-free village"],
                ["Gornergrat Railway to see Matterhorn", "Matterhorn Museum visit", "Traditional Swiss lunch", "Explore Zermatt village"],
                ["Cable car to Klein Matterhorn", "Glacier skiing or snowboarding", "Mountain restaurant dining", "Spa relaxation at hotel"],
                ["Sunnegga-Rothorn excursion", "Winter hiking trails", "Swiss chocolate tasting", "Shopping for Swiss goods"],
                ["Gornergrat sunrise trip", "Photography at Riffelsee lake", "Traditional raclette dinner", "Alpine wellness"],
                ["Final Matterhorn views", "Souvenir shopping", "Leisurely village walk", "Hotel checkout and departure"],
            ][:duration]
        elif any(keyword in destination_lower for keyword in ["banff", "canada", "canadian"]):
            return [
                ["Arrival in Calgary", "Transfer to Banff National Park", "Hotel check-in", "Evening walk in Banff townsite"],
                ["Lake Louise visit", "Skiing at Lake Louise Ski Resort", "Ice walk on frozen lake", "Mountain lodge dinner"],
                ["Moraine Lake (if accessible)", "Banff Gondola ride", "Cave and Basin Historic Site", "Hot springs relaxation"],
                ["Johnston Canyon ice walk", "Cross-country skiing", "Wildlife viewing", "Canadian cuisine experience"],
                ["Sunshine Village skiing", "Snowshoeing adventures", "Banff Avenue shopping", "Local brewery visit"],
                ["Final mountain views", "Souvenir shopping", "Check-out", "Transfer to Calgary for departure"],
            ][:duration]
        else:
            # Generic activities for other destinations
            activities = [
                ["Arrival", "Airport transfer", "Hotel check-in", "Explore local neighborhood"],
                ["City tour", "Major attractions visit", "Local cuisine lunch", "Cultural site exploration"],
                ["Day trip/excursion", "Outdoor activities", "Shopping district visit", "Traditional dinner"],
                ["Museum/gallery visits", "Local market exploration", "Cooking class/food tour", "Entertainment district"],
                ["Nature/outdoor activities", "Scenic viewpoints", "Local experiences", "Relaxation time"],
                ["Final sightseeing", "Souvenir shopping", "Hotel checkout", "Departure preparation"],
            ]
            return activities[:duration] + [["Leisure day", "Personal exploration", "Rest and relaxation"]] * max(0, duration - len(activities))
    
    def _get_destination_meals(self, destination: str, loyalty_tier: str) -> List[str]:
        """Get destination-specific meal recommendations"""
        destination_lower = destination.lower()
        tier_prefix = "Premium " if loyalty_tier in ["GOLD", "PLATINUM"] else ""
        
        if any(keyword in destination_lower for keyword in ["zermatt", "switzerland"]):
            return [f"{tier_prefix}Swiss specialties", f"{tier_prefix}Fondue or raclette", f"{tier_prefix}Alpine cuisine"]
        elif any(keyword in destination_lower for keyword in ["banff", "canada"]):
            return [f"{tier_prefix}Canadian cuisine", f"{tier_prefix}Mountain lodge dining", f"{tier_prefix}Local specialties"]
        else:
            return [f"{tier_prefix}Local cuisine", f"{tier_prefix}Traditional dishes", f"{tier_prefix}Regional specialties"]
    
    def _get_destination_highlights(self, destination: str, event_details: Dict[str, Any] = None) -> List[str]:
        """Get destination-specific highlights including events and popular attractions"""
        destination_lower = destination.lower()
        highlights = []
        
        # Add event highlights first if available
        if event_details:
            event_name = event_details.get("name", "")
            event_description = event_details.get("description", "")
            if event_name:
                highlights.append(f"{event_name} - special festival celebration")
        
        # Add destination-specific attractions
        if any(keyword in destination_lower for keyword in ["bangkok", "thailand"]):
            highlights.extend([
                "Grand Palace and Wat Phra Kaew",
                "Wat Arun (Temple of Dawn)",
                "Chatuchak Weekend Market",
                "Chao Phraya River boat tours",
                "Thai street food experiences",
                "Floating markets",
                "Traditional Thai massage"
            ])
        elif any(keyword in destination_lower for keyword in ["bengaluru", "bangalore", "india"]):
            highlights.extend([
                "Lalbagh Botanical Garden",
                "Bangalore Palace",
                "Vidhana Soudha architecture",
                "Cubbon Park and museums",
                "Traditional South Indian cuisine",
                "Local markets and shopping",
                "Brewery culture and nightlife"
            ])
        elif any(keyword in destination_lower for keyword in ["paris", "france"]):
            highlights.extend([
                "Eiffel Tower and Trocadéro views",
                "Louvre Museum and Mona Lisa",
                "Notre-Dame Cathedral",
                "Champs-Élysées and Arc de Triomphe",
                "Seine River cruise",
                "Montmartre and Sacré-Cœur",
                "French cuisine and café culture"
            ])
        elif any(keyword in destination_lower for keyword in ["tokyo", "japan"]):
            highlights.extend([
                "Senso-ji Temple in Asakusa",
                "Tokyo Skytree and city views",
                "Shibuya Crossing",
                "Meiji Shrine and Harajuku",
                "Tsukiji Outer Market",
                "Traditional and modern architecture",
                "Japanese cuisine experiences"
            ])
        elif any(keyword in destination_lower for keyword in ["zermatt", "switzerland"]):
            highlights.extend([
                "Iconic Matterhorn mountain views",
                "Gornergrat Railway scenic journey",
                "World-class Alpine skiing",
                "Charming car-free village",
                "Swiss culinary experiences",
                "Luxury mountain hospitality"
            ])
        elif any(keyword in destination_lower for keyword in ["banff", "canada"]):
            highlights.extend([
                "Stunning Rocky Mountain scenery",
                "World-class skiing at multiple resorts",
                "Pristine lakes and glaciers",
                "Abundant wildlife viewing",
                "Natural hot springs relaxation",
                "Canadian hospitality and cuisine"
            ])
        else:
            # Generic highlights for unknown destinations
            highlights.extend([
                f"Explore the beauty of {destination}",
                "Immerse in local culture",
                "Experience regional cuisine",
                "Visit iconic landmarks",
                "Enjoy local hospitality"
            ])
        
        return highlights
    
    def _get_destination_tips(self, destination: str, loyalty_tier: str) -> List[str]:
        """Get destination-specific travel tips"""
        destination_lower = destination.lower()
        base_tips = []
        
        if any(keyword in destination_lower for keyword in ["zermatt", "switzerland"]):
            base_tips = [
                "Pack warm layers for mountain weather",
                "Swiss Pass recommended for train travel",
                "Restaurants close early - plan dinner accordingly",
                "Cash preferred at some local establishments",
                "Book Gornergrat Railway in advance during peak season"
            ]
        elif any(keyword in destination_lower for keyword in ["banff", "canada"]):
            base_tips = [
                "Layer clothing for changing mountain weather",
                "Book ski equipment rental in advance",
                "Parks Canada Discovery Pass recommended",
                "Winter driving conditions - consider shuttle services",
                "Wildlife encounters possible - maintain safe distances"
            ]
        else:
            base_tips = [
                "Check weather forecast before departure",
                "Pack appropriate clothing for activities",
                "Keep important documents secure",
                "Learn basic local phrases",
                "Respect local customs and traditions"
            ]
        
        if loyalty_tier in ["GOLD", "PLATINUM"]:
            base_tips.append(f"Your {loyalty_tier} status includes priority services and exclusive benefits")
        
        return base_tips
    
    def _get_default_destination_info(self, destination: str) -> Dict[str, Any]:
        """Provide basic destination information as fallback"""
        if not destination:
            return {
                "description": "Exciting travel destination with unique experiences awaiting discovery.",
                "best_time_to_visit": "Check seasonal weather patterns for optimal travel timing",
                "local_culture": "Research local customs and traditions before your visit",
                "currency": "Check current exchange rates for local currency",
                "language": "Learn basic phrases in the local language",
                "timezone": "Verify timezone difference from your departure location"
            }
        
        # Basic destination info based on common destinations
        destination_lower = destination.lower()
        
        if 'japan' in destination_lower or 'tokyo' in destination_lower:
            return {
                "description": "Japan offers a fascinating blend of ancient traditions and cutting-edge modernity, from serene temples to bustling metropolises.",
                "best_time_to_visit": "Spring (March-May) for cherry blossoms, Fall (September-November) for mild weather",
                "local_culture": "Bow as greeting, remove shoes indoors, quiet on public transport, tipping not customary",
                "currency": "Japanese Yen (JPY), approximately ¥150 = $1 USD",
                "language": "Japanese (some English in tourist areas)",
                "timezone": "JST (UTC+9), typically 13-16 hours ahead of US time zones",
                "popular_attractions": ["Senso-ji Temple", "Tokyo Skytree", "Shibuya Crossing", "Meiji Shrine", "Tsukiji Market", "Imperial Palace", "Harajuku District"],
                "event_highlights": "Experience traditional festivals, cherry blossom season, and modern celebrations"
            }
        elif 'india' in destination_lower or 'bengaluru' in destination_lower or 'bangalore' in destination_lower:
            return {
                "description": "India's Silicon Valley, Bengaluru combines modern tech culture with rich history, beautiful gardens, and vibrant traditions.",
                "best_time_to_visit": "October to March for pleasant weather, avoid monsoon season (June-September)",
                "local_culture": "Namaste greeting, dress modestly at religious sites, diverse languages and customs",
                "currency": "Indian Rupee (INR), approximately ₹83 = $1 USD",
                "language": "English and Kannada widely spoken, Hindi understood",
                "timezone": "IST (UTC+5:30), typically 10.5-13.5 hours ahead of US time zones",
                "popular_attractions": ["Lalbagh Botanical Garden", "Bangalore Palace", "Vidhana Soudha", "Cubbon Park", "ISCKON Temple", "Commercial Street", "UB City Mall"],
                "event_highlights": "Experience local festivals, traditional celebrations, and cultural events"
            }
        elif 'thailand' in destination_lower or 'bangkok' in destination_lower:
            return {
                "description": "Thailand captivates with golden temples, pristine beaches, vibrant street food culture, and warm hospitality.",
                "best_time_to_visit": "Cool season (November-February) for best weather, avoid rainy season (May-October)",
                "local_culture": "Wai greeting (prayer-like gesture), dress modestly at temples, remove shoes when entering homes",
                "currency": "Thai Baht (THB), approximately ฿35 = $1 USD",
                "language": "Thai (English widely spoken in tourist areas)",
                "timezone": "ICT (UTC+7), typically 12-15 hours ahead of US time zones",
                "popular_attractions": ["Grand Palace", "Wat Pho Temple", "Wat Arun", "Chatuchak Market", "Chao Phraya River", "Floating Markets", "Khao San Road"],
                "event_highlights": "Experience local festivals, temple ceremonies, and traditional celebrations"
            }
        elif 'france' in destination_lower or 'paris' in destination_lower:
            return {
                "description": "France enchants with world-class art, exquisite cuisine, stunning architecture, and rich cultural heritage.",
                "best_time_to_visit": "Spring (April-June) and Fall (September-October) for pleasant weather and fewer crowds",
                "local_culture": "Greet with 'Bonjour/Bonsoir', dress elegantly, dining is leisurely, tipping 10% is appreciated",
                "currency": "Euro (EUR), approximately €0.85 = $1 USD",
                "language": "French (English spoken in tourist areas, learning basic French phrases appreciated)",
                "timezone": "CET (UTC+1), typically 6-9 hours ahead of US time zones",
                "popular_attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Arc de Triomphe", "Champs-Élysées", "Montmartre", "Seine River Cruise"],
                "event_highlights": "Experience French festivals, art exhibitions, and cultural celebrations"
            }
        else:
            # Generic fallback for unknown destinations
            return {
                "description": f"{destination} offers unique cultural experiences, local cuisine, and memorable attractions for travelers.",
                "best_time_to_visit": "Research seasonal weather patterns and local events for optimal timing",
                "local_culture": "Learn about local customs, dress codes, and social etiquette before arrival",
                "currency": "Check current exchange rates and payment methods commonly accepted",
                "language": "Research primary language and useful phrases for travelers",
                "timezone": "Verify timezone difference and plan for jet lag adjustment",
                "popular_attractions": ["Major landmarks", "Cultural sites", "Local markets", "Museums", "Religious sites", "Natural attractions"],
                "event_highlights": "Discover local festivals, cultural events, and seasonal celebrations"
            }
    
    def _generate_travel_readiness(self, requirements: Dict[str, Any]) -> List[TravelReadinessItem]:
        """Generate destination-specific travel readiness checklist"""
        
        items = []
        destination = requirements.get("destination", "").lower()
        departure_date = requirements.get("departure_date", "")
        
        # Documents - Enhanced based on destination
        items.append(TravelReadinessItem(
            category="documents",
            item="Valid passport",
            status="required",
            deadline="Immediate",
            details="Passport must be valid for at least 6 months beyond travel dates"
        ))
        
        # Visa requirements based on destination
        if any(keyword in destination for keyword in ["switzerland", "zermatt"]):
            items.append(TravelReadinessItem(
                category="documents",
                item="Schengen Area visa check",
                status="required",
                deadline="45 days before departure",
                details="US citizens: No visa needed for stays under 90 days. Other nationalities: Check Schengen requirements"
            ))
        elif any(keyword in destination for keyword in ["canada", "banff"]):
            items.append(TravelReadinessItem(
                category="documents",
                item="eTA or visa for Canada",
                status="required",
                deadline="30 days before departure",
                details="US citizens: No eTA needed. Other nationalities: Apply for eTA online or check visa requirements"
            ))
        else:
            items.append(TravelReadinessItem(
                category="documents",
                item="Visa requirements check",
                status="required",
                deadline="30 days before departure",
                details="Check if destination requires visa for your nationality"
            ))
        
        # Health requirements
        items.append(TravelReadinessItem(
            category="health",
            item="Travel health consultation",
            status="recommended",
            deadline="4-6 weeks before departure",
            details="Consult travel medicine specialist for destination-specific health advice"
        ))
        
        if any(keyword in destination for keyword in ["switzerland", "zermatt", "banff", "canada"]):
            items.append(TravelReadinessItem(
                category="health",
                item="Winter sports insurance",
                status="required",
                deadline="7 days before departure",
                details="Ensure travel insurance covers winter sports activities and potential mountain rescue"
            ))
        
        # Insurance - Enhanced
        items.append(TravelReadinessItem(
            category="insurance",
            item="Comprehensive travel insurance",
            status="required",
            deadline="7 days before departure",
            details="Coverage should include medical, trip cancellation, and emergency evacuation"
        ))
        
        # Logistics - Destination specific
        if any(keyword in destination for keyword in ["switzerland", "zermatt"]):
            items.append(TravelReadinessItem(
                category="logistics",
                item="Swiss Francs currency",
                status="recommended",
                deadline="1 week before departure",
                details="Switzerland primarily uses Swiss Francs. Cards widely accepted but cash useful for small vendors"
            ))
            items.append(TravelReadinessItem(
                category="logistics",
                item="Winter gear check",
                status="required",
                deadline="2 weeks before departure",
                details="Pack warm layers, waterproof clothing, and proper winter footwear for mountain conditions"
            ))
        elif any(keyword in destination for keyword in ["canada", "banff"]):
            items.append(TravelReadinessItem(
                category="logistics",
                item="Canadian Dollars currency",
                status="recommended",
                deadline="1 week before departure",
                details="Exchange some CAD for immediate needs. Cards widely accepted throughout Canada"
            ))
            items.append(TravelReadinessItem(
                category="logistics",
                item="Cold weather preparation",
                status="required",
                deadline="2 weeks before departure",
                details="Pack layers, winter boots, gloves, and hat for Canadian winter conditions"
            ))
        else:
            items.append(TravelReadinessItem(
                category="logistics",
                item="Local currency research",
                status="recommended",
                deadline="1 week before departure",
                details="Research local currency and payment methods accepted at destination"
            ))
        
        # Additional seasonal considerations
        if departure_date and "2025-11" in departure_date:
            items.append(TravelReadinessItem(
                category="logistics",
                item="November weather preparation",
                status="required",
                deadline="1 week before departure",
                details="November can have variable weather - pack for both cold and mild conditions"
            ))
        
        return items
    
    def _generate_next_steps(self, input_data: Dict[str, Any]) -> List[str]:
        """Generate next steps for booking process"""
        
        steps = []
        
        flight_offers = input_data.get("flight_offers", [])
        hotel_offers = input_data.get("hotel_offers", [])
        
        if flight_offers:
            steps.append("Review and select preferred flight option")
        else:
            steps.append("Search for flights based on itinerary")
        
        if hotel_offers:
            steps.append("Review and select accommodation")
        else:
            steps.append("Search for hotels in destination")
        
        steps.extend([
            "Confirm all travel dates and requirements",
            "Review total cost and payment options",
            "Check visa and documentation requirements",
            "Consider travel insurance options",
            "Book selected flights and hotels"
        ])
        
        return steps
    
    async def _generate_fallback_itinerary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate minimal fallback itinerary with images"""
        
        requirements = input_data.get("requirements", {})
        events = input_data.get("events", [])
        destination = requirements.get("destination", "Destination")
        
        # Generate images for the fallback itinerary
        try:
            hero_images, gallery_images = await self._generate_itinerary_images(
                destination, events, requirements
            )
        except Exception as e:
            self.log(f"⚠️ Image generation failed in fallback: {str(e)}")
            hero_images, gallery_images = [], []
        
        # Generate detailed days based on event schedule if available
        days = self._create_detailed_days_from_events(
            events, destination, requirements
        )
        
        # Create enhanced highlights from events
        highlights = self._extract_event_highlights(events, destination)
        
        fallback_itinerary = Itinerary(
            title=f"Diwali Festival Trip to {destination}" if any("diwali" in str(event).lower() for event in events) else f"Trip to {destination}",
            destination=destination,
            destination_info=self._get_default_destination_info(destination),
            duration=requirements.get("duration", 5),
            traveler_count=requirements.get("passengers", 2),
            departure_date=requirements.get("departure_date", "2025-10-20"),
            return_date=requirements.get("return_date") or "2025-10-24",
            days=days,
            flights=[],
            accommodations=[],
            hero_images=hero_images,
            gallery_images=gallery_images,
            total_cost={"total": 1500, "currency": "USD"},
            travel_readiness=[],
            rationale="Comprehensive travel plan with cultural events and authentic experiences",
            highlights=highlights,
            tips=["Dress modestly at temples", "Carry cash for local markets", "Respect religious customs", "Book accommodations early during festival season"]
        )
        
        fallback_result = PrepareItineraryResult(
            itinerary=fallback_itinerary,
            confidence_score=0.3,
            personalization_applied=False,
            next_steps=["Complete travel planning", "Book flights and hotels"]
        )
        
        return self.format_output(fallback_result.model_dump())

    async def _generate_itinerary_images(self, destination: str, event_details: Dict[str, Any], requirements: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate hero and gallery images for the itinerary using ImageSearchAgent"""
        try:
            hero_images = []
            gallery_images = []
            
            # Extract event information
            event_name = ""
            if event_details and isinstance(event_details, list) and event_details:
                event_name = event_details[0].get("name", "")
            elif event_details and isinstance(event_details, dict):
                event_name = event_details.get("name", "")
            elif requirements:
                event_name = requirements.get("event_name", "")
            
            # Generate hero images (main showcase)
            hero_search_data = {
                "event_name": event_name,
                "destination": destination,
                "activity_type": "destination_highlight",
                "context": "itinerary_overview",
                "image_count": 2
            }
            
            hero_result = await self.image_agent.execute(hero_search_data, "itinerary_hero")
            # Images can be in data.images or directly in images
            if hero_result.get("data", {}).get("images"):
                hero_images = hero_result["data"]["images"]
            elif hero_result.get("images"):
                hero_images = hero_result["images"]
            
            # Generate gallery images (additional content)
            gallery_search_data = {
                "event_name": event_name,
                "destination": destination,
                "activity_type": "cultural_experience",
                "context": "destination_gallery", 
                "image_count": 4
            }
            
            gallery_result = await self.image_agent.execute(gallery_search_data, "itinerary_gallery")
            # Images can be in data.images or directly in images
            if gallery_result.get("data", {}).get("images"):
                gallery_images = gallery_result["data"]["images"]
            elif gallery_result.get("images"):
                gallery_images = gallery_result["images"]
            
            # If we have event-specific images, also get event highlights
            if event_name:
                event_search_data = {
                    "event_name": event_name,
                    "destination": destination,
                    "activity_type": "event_celebration",
                    "context": "event_highlight",
                    "image_count": 3
                }
                
                event_result = await self.image_agent.execute(event_search_data, "itinerary_event")
                # Images can be in data.images or directly in images
                if event_result.get("data", {}).get("images"):
                    gallery_images.extend(event_result["data"]["images"])
                elif event_result.get("images"):
                    gallery_images.extend(event_result["images"])
            
            self.log(f"✅ Generated {len(hero_images)} hero images and {len(gallery_images)} gallery images")
            return hero_images, gallery_images
            
        except Exception as e:
            self.log(f"⚠️ Image generation failed: {str(e)} - using empty image arrays")
            return [], []

    def _create_detailed_days_from_events(self, events: List[Dict[str, Any]], destination: str, requirements: Dict[str, Any]) -> List[ItineraryDay]:
        """Create detailed daily itinerary from event schedule data"""
        days = []
        
        if not events:
            return days
            
        # Get the first event (primary event like Diwali)
        event = events[0] if isinstance(events, list) else events
        if not isinstance(event, dict):
            return days
            
        event_schedule = event.get("schedule", [])
        departure_date = requirements.get("departure_date", "2025-10-20")
        
        # Create days from event schedule
        for i, day_schedule in enumerate(event_schedule[:5], 1):  # Limit to 5 days
            try:
                from datetime import datetime, timedelta
                base_date = datetime.fromisoformat(departure_date)
                current_date = (base_date + timedelta(days=i-1)).isoformat()[:10]
            except:
                current_date = departure_date
                
            # Extract activities from the day's schedule
            activities = []
            
            # Add arrival/departure activities for first/last day
            if i == 1:
                activities.extend([
                    "Arrival at Kempegowda International Airport",
                    "Check-in to hotel in central Bangalore",
                    "Afternoon rest and exploration of local area"
                ])
            
            # Add the main event activity
            activity_description = day_schedule.get("activity", "")
            if activity_description:
                activities.append(f"🎭 {activity_description}")
            
            # Add specific highlights from the event
            highlights = day_schedule.get("highlights", [])
            for highlight in highlights[:3]:  # Limit to 3 highlights per day
                activities.append(f"✨ {highlight}")
            
            # Add general Bangalore activities
            if "bangalore" in destination.lower():
                if i == 1:
                    activities.append("Evening walk through Commercial Street")
                elif i == 2:
                    activities.extend([
                        "Morning visit to Lalbagh Botanical Garden",
                        "Explore Bangalore Palace and grounds"
                    ])
                elif i == 3:
                    activities.extend([
                        "Visit ISKCON Temple for special ceremonies",
                        "Traditional South Indian lunch"
                    ])
                elif i == 4:
                    activities.extend([
                        "Cubbon Park morning walk",
                        "Local market exploration"
                    ])
                elif i == 5:
                    activities.extend([
                        "Final temple visits and blessings",
                        "Souvenir shopping",
                        "Departure to airport"
                    ])
            
            # Create the day
            day = ItineraryDay(
                day=i,
                date=current_date,
                location=destination,
                activities=activities,
                accommodation={"type": "hotel", "name": "Selected Hotel", "benefits": "Festival season booking"} if i < len(event_schedule) else None,
                transportation={"type": "arrival", "details": "Airport transfer"} if i == 1 else None,
                meals=["Breakfast", "Traditional festival lunch", "Local dinner"],
                budget_estimate=300.0  # Daily budget estimate
            )
            
            days.append(day)
            
        return days
    
    def _extract_event_highlights(self, events: List[Dict[str, Any]], destination: str) -> List[str]:
        """Extract highlights from event data"""
        highlights = []
        
        if not events:
            return ["Travel to destination", "Experience local culture"]
            
        event = events[0] if isinstance(events, list) else events
        if not isinstance(event, dict):
            return ["Travel to destination", "Experience local culture"]
        
        # Add event-specific highlights
        event_name = event.get("name", "")
        if event_name:
            highlights.append(f"Experience {event_name} celebrations")
            
        # Add cultural significance
        cultural_significance = event.get("cultural_significance", "")
        if cultural_significance:
            highlights.append("Immerse in rich cultural traditions")
            
        # Add schedule highlights
        schedule = event.get("schedule", [])
        for day_schedule in schedule[:3]:  # First 3 days
            activity = day_schedule.get("activity", "")
            if activity:
                highlights.append(f"Participate in {activity}")
        
        # Add destination-specific highlights
        if "bangalore" in destination.lower():
            highlights.extend([
                "Explore historic Bangalore Palace",
                "Visit beautiful Lalbagh Botanical Garden",
                "Experience vibrant local markets",
                "Discover traditional South Indian cuisine"
            ])
        
        return highlights[:8]  # Limit to 8 highlights