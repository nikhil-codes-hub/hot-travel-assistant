import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
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
    title: str = Field(..., description="Itinerary title")
    destination: str = Field(..., description="Primary destination")
    duration: int = Field(..., description="Trip duration in days")
    traveler_count: int = Field(..., description="Number of travelers")
    departure_date: str = Field(..., description="Departure date")
    return_date: str = Field(..., description="Return date")
    
    # Trip components
    days: List[ItineraryDay] = Field(..., description="Day-by-day itinerary")
    flights: List[Dict[str, Any]] = Field([], description="Flight details")
    accommodations: List[Dict[str, Any]] = Field([], description="Hotel details")
    total_cost: Dict[str, Any] = Field(..., description="Total trip cost breakdown")
    
    # Travel readiness
    travel_readiness: List[TravelReadinessItem] = Field([], description="Travel preparation checklist")
    
    # Rationale and insights
    rationale: str = Field(..., description="Why this itinerary works")
    highlights: List[str] = Field(..., description="Trip highlights")
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
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                self.ai_available = True
        except Exception:
            self.ai_available = False
    
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
    
    async def _create_ai_itinerary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create itinerary using AI for coherent planning"""
        
        prompt = self._create_itinerary_prompt(input_data)
        response = self.model.generate_content(prompt)
        
        try:
            # Parse AI response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            ai_data = json.loads(response_text)
            
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
            departure_date=overview.get("departure_date", requirements.get("departure_date", "")),
            return_date=overview.get("return_date", ""),
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
        """Create itinerary using rule-based logic"""
        
        requirements = input_data.get("requirements", {})
        duration = requirements.get("duration", 7)
        destination = requirements.get("destination", "Destination")
        departure_date = requirements.get("departure_date", "2024-06-01")
        
        # Calculate return date
        try:
            dep_date = datetime.fromisoformat(departure_date)
            return_date = (dep_date + timedelta(days=duration-1)).isoformat()[:10]
        except:
            return_date = departure_date
        
        # Create basic daily plan
        days = []
        for i in range(duration):
            try:
                current_date = (datetime.fromisoformat(departure_date) + timedelta(days=i)).isoformat()[:10]
            except:
                current_date = departure_date
            
            if i == 0:
                activities = ["Arrival", "Airport transfer", "Hotel check-in", "Rest and explore nearby area"]
            elif i == duration - 1:
                activities = ["Final sightseeing", "Shopping for souvenirs", "Hotel checkout", "Departure"]
            else:
                activities = ["Morning sightseeing", "Lunch break", "Afternoon activities", "Evening relaxation"]
            
            day = ItineraryDay(
                day=i + 1,
                date=current_date,
                location=destination,
                activities=activities,
                accommodation=None,
                transportation=None,
                meals=["Local cuisine recommendation"],
                budget_estimate=100.0
            )
            days.append(day)
        
        # Build travel readiness
        travel_readiness = self._generate_travel_readiness(requirements)
        
        # Create itinerary
        itinerary = Itinerary(
            title=f"{duration}-Day Trip to {destination}",
            destination=destination,
            duration=duration,
            traveler_count=requirements.get("passengers", 1),
            departure_date=departure_date,
            return_date=return_date,
            days=days,
            flights=[],
            accommodations=[],
            total_cost={
                "flights": 800,
                "hotels": duration * 100,
                "activities": duration * 50,
                "meals": duration * 75,
                "total": 800 + (duration * 225),
                "currency": "USD"
            },
            travel_readiness=travel_readiness,
            rationale=f"Basic {duration}-day itinerary for {destination} with standard activities and logistics",
            highlights=[f"Explore {destination}", "Experience local culture", "Relaxation and sightseeing"],
            tips=["Check weather forecast", "Pack appropriate clothing", "Keep important documents safe"]
        )
        
        result = PrepareItineraryResult(
            itinerary=itinerary,
            confidence_score=0.6,
            personalization_applied=bool(input_data.get("customer_profile")),
            next_steps=self._generate_next_steps(input_data)
        )
        
        return result.model_dump()
    
    def _generate_travel_readiness(self, requirements: Dict[str, Any]) -> List[TravelReadinessItem]:
        """Generate travel readiness checklist"""
        
        items = []
        
        # Documents
        items.append(TravelReadinessItem(
            category="documents",
            item="Valid passport",
            status="required",
            deadline=None,
            details="Passport must be valid for at least 6 months beyond travel dates"
        ))
        
        items.append(TravelReadinessItem(
            category="documents",
            item="Visa requirements check",
            status="required",
            deadline="30 days before departure",
            details="Check if destination requires visa for your nationality"
        ))
        
        # Health
        items.append(TravelReadinessItem(
            category="health",
            item="Vaccination requirements",
            status="recommended",
            deadline="4 weeks before departure",
            details="Check CDC recommendations for destination"
        ))
        
        # Insurance
        items.append(TravelReadinessItem(
            category="insurance",
            item="Travel insurance",
            status="recommended",
            deadline="7 days before departure",
            details="Consider comprehensive coverage including medical and trip cancellation"
        ))
        
        # Logistics
        items.append(TravelReadinessItem(
            category="logistics",
            item="Currency exchange",
            status="optional",
            deadline="1 week before departure",
            details="Exchange some local currency for immediate needs upon arrival"
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
            return_date=requirements.get("return_date", "2024-06-08"),
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