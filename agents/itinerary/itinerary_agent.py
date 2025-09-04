import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent

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
    duration: int = Field(7, description="Trip duration in days")
    traveler_count: int = Field(1, description="Number of travelers")
    departure_date: str = Field("TBD", description="Departure date")
    return_date: str = Field("TBD", description="Return date")
    
    # Trip components
    days: List[ItineraryDay] = Field([], description="Day-by-day itinerary")
    flights: List[Dict[str, Any]] = Field([], description="Flight details")
    accommodations: List[Dict[str, Any]] = Field([], description="Hotel details")
    total_cost: Dict[str, Any] = Field({"currency": "USD", "total": 0}, description="Total trip cost breakdown")
    
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
        self.ai_provider = os.getenv("AI_PROVIDER", "gemini")
        self.ai_available = False
        
        try:
            if self.ai_provider == "vertex":
                # Initialize Vertex AI
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("VERTEX_AI_LOCATION")
                if project_id and location:
                    aiplatform.init(project=project_id, location=location)
                    self.model = None  # Will use aiplatform.gapic.PredictionServiceClient
                    self.ai_available = True
            else:
                # Initialize Gemini
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel('gemini-2.0-flash')
                    self.ai_available = True
        except Exception:
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
                result = await self._create_ai_itinerary(input_data)
            else:
                result = self._create_rule_based_itinerary(input_data)
            
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"PrepareItineraryAgent error: {e}")
            return self._generate_fallback_itinerary(input_data)
    
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
            return self._create_rule_based_itinerary(input_data)
    
    def _create_itinerary_prompt(self, input_data: Dict[str, Any]) -> str:
        """Create AI prompt for itinerary generation"""
        
        requirements = input_data.get("requirements", {})
        customer_profile = input_data.get("customer_profile", {})
        flight_offers = input_data.get("flight_offers", [])
        hotel_offers = input_data.get("hotel_offers", [])
        
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
        
        return f"""
Create a detailed travel itinerary for this trip. Be specific and practical.

TRIP REQUIREMENTS:
- Destination: {destination}
- Duration: {duration} days
- Travelers: {passengers}
- Departure: {departure_date}
- Budget: {budget or "Not specified"}

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
    "highlights": ["Key experiences", "Must-see attractions", "Unique opportunities"],
    "travel_tips": ["Practical advice", "Local insights", "Money-saving tips"],
    "confidence_score": 0.0-1.0
}}

Focus on:
1. Realistic day-by-day planning
2. Logical flow and pacing
3. Budget considerations
4. Customer preferences alignment
5. Practical logistics (check-in times, travel times)
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
    
    def _create_rule_based_itinerary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Extract event information
        events = event_details.get("events", [])
        main_event = events[0] if events else None
        event_name = requirements.get("event_name")
        
        # Create personalized highlights and tips with event information
        highlights = self._get_destination_highlights(destination)
        tips = self._get_destination_tips(destination, loyalty_tier)
        
        # Add event-specific highlights and tips
        if main_event:
            event_highlights = [
                f"🎪 {main_event.get('name', event_name)} Experience",
                f"📅 Event Date: {main_event.get('start_date')}",
                f"📍 Event Location: {main_event.get('venue', main_event.get('location'))}",
            ]
            highlights = event_highlights + highlights
            
            # Add event-specific tips
            if main_event.get('what_to_bring'):
                event_tips = [f"🎒 For the event: {', '.join(main_event['what_to_bring'][:3])}"]
                tips = event_tips + tips
                
        elif event_name:
            # Even without detailed event info, mention the event
            highlights = [f"🎪 {event_name} in {destination}"] + highlights
        
        # Enhanced rationale with event focus
        rationale = f"This {duration}-day itinerary for {destination} is curated for {passengers} travelers with {loyalty_tier} tier benefits. "
        
        if main_event or event_name:
            event_display_name = main_event.get('name') if main_event else event_name
            rationale += f"🎪 **EVENT FOCUS**: Built around the {event_display_name} experience. "
            if main_event and main_event.get('cultural_significance'):
                rationale += f"This {main_event.get('event_type', 'event')} offers {main_event['cultural_significance'][:100]}... "
                
        if destination_suggestions:
            rationale += f"Selected from recommended destinations based on your preferences. "
            
        if main_event or event_name:
            rationale += f"The itinerary ensures you experience the event while also exploring {destination}'s cultural attractions and maximizing your {loyalty_tier} member benefits."
        else:
            rationale += f"The plan balances sightseeing, relaxation, and cultural experiences while maximizing your {loyalty_tier} member benefits."
        
        # Create event-focused title if applicable
        if main_event or event_name:
            event_display_name = main_event.get('name') if main_event else event_name
            title = f"{duration}-Day {event_display_name} Experience in {destination}"
        else:
            title = f"{duration}-Day Premium Trip to {destination}"
            
        # Create itinerary
        itinerary = Itinerary(
            title=title,
            destination=destination,
            duration=duration,
            traveler_count=passengers,
            departure_date=departure_date,
            return_date=return_date,
            days=days,
            flights=flight_offers[:2] if flight_offers else [],
            accommodations=hotel_offers[:3] if hotel_offers else [],
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
    
    def _get_destination_highlights(self, destination: str) -> List[str]:
        """Get destination-specific highlights"""
        destination_lower = destination.lower()
        
        if any(keyword in destination_lower for keyword in ["zermatt", "switzerland"]):
            return [
                "Iconic Matterhorn mountain views",
                "Gornergrat Railway scenic journey",
                "World-class Alpine skiing",
                "Charming car-free village",
                "Swiss culinary experiences",
                "Luxury mountain hospitality"
            ]
        elif any(keyword in destination_lower for keyword in ["banff", "canada"]):
            return [
                "Stunning Rocky Mountain scenery",
                "World-class skiing at multiple resorts",
                "Pristine lakes and glaciers",
                "Abundant wildlife viewing",
                "Natural hot springs relaxation",
                "Canadian hospitality and cuisine"
            ]
        else:
            return [
                f"Explore the beauty of {destination}",
                "Immerse in local culture",
                "Experience regional cuisine",
                "Visit iconic landmarks",
                "Enjoy local hospitality"
            ]
    
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
    
    def _generate_fallback_itinerary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate minimal fallback itinerary"""
        
        requirements = input_data.get("requirements", {})
        
        fallback_itinerary = Itinerary(
            title="Travel Plan",
            destination=requirements.get("destination", "Destination"),
            duration=requirements.get("duration", 7),
            traveler_count=requirements.get("passengers", 1),
            departure_date=requirements.get("departure_date", "2024-06-01"),
            return_date=requirements.get("return_date") or "2024-06-08",
            days=[],
            flights=[],
            accommodations=[],
            total_cost={"total": 0, "currency": "USD"},
            travel_readiness=[],
            rationale="Basic travel plan - detailed itinerary generation not available",
            highlights=["Travel to destination", "Experience local attractions"],
            tips=["Check travel requirements", "Pack appropriately"]
        )
        
        fallback_result = PrepareItineraryResult(
            itinerary=fallback_itinerary,
            confidence_score=0.3,
            personalization_applied=False,
            next_steps=["Complete travel planning", "Book flights and hotels"]
        )
        
        return self.format_output(fallback_result.model_dump())