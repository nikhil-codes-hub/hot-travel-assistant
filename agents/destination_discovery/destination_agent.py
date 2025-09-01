import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent

class DestinationSuggestion(BaseModel):
    destination: str = Field(..., description="Destination name")
    country: str = Field(..., description="Country")
    reason: str = Field(..., description="Why this destination fits")
    season_score: float = Field(..., description="Seasonal suitability 0.0-1.0")
    budget_fit: str = Field(..., description="Budget compatibility: low/medium/high/luxury")
    highlights: List[str] = Field(..., description="Key attractions/experiences")
    best_duration: str = Field(..., description="Recommended stay duration")

class DestinationDiscoveryResult(BaseModel):
    suggestions: List[DestinationSuggestion]
    search_criteria: Dict[str, Any]
    confidence_score: float
    seasonality_considered: bool

class DestinationDiscoveryAgent(BaseAgent):
    def __init__(self):
        super().__init__("DestinationDiscoveryAgent")
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
        Discover destinations based on vague criteria
        
        Input:
        - destination_type: beach/mountains/city/adventure/cultural etc
        - budget: numeric amount or range
        - budget_currency: USD/EUR etc
        - departure_date: for seasonality
        - duration: trip length
        - passengers: number of travelers
        - nationality: for visa considerations
        - special_requirements: accessibility, activities etc
        """
        self.validate_input(input_data, [])  # No required fields - can work with minimal input
        
        if not self.ai_available:
            return self._generate_fallback_suggestions(input_data)
        
        try:
            prompt = self._create_discovery_prompt(input_data)
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text, input_data)
            return self.format_output(result)
            
        except Exception as e:
            return self._generate_fallback_suggestions(input_data)
    
    def _create_discovery_prompt(self, input_data: Dict[str, Any]) -> str:
        destination_type = input_data.get("destination_type")
        budget = input_data.get("budget")
        budget_currency = input_data.get("budget_currency", "USD")
        departure_date = input_data.get("departure_date")
        duration = input_data.get("duration", 7)
        passengers = input_data.get("passengers", 1)
        nationality = input_data.get("nationality", "US")
        special_requirements = input_data.get("special_requirements", [])
        
        # Determine current season for departure
        season_context = ""
        if departure_date:
            try:
                dep_date = datetime.fromisoformat(departure_date)
                month = dep_date.month
                if month in [12, 1, 2]:
                    season_context = "Winter departure (Dec-Feb)"
                elif month in [3, 4, 5]:
                    season_context = "Spring departure (Mar-May)"
                elif month in [6, 7, 8]:
                    season_context = "Summer departure (Jun-Aug)"
                else:
                    season_context = "Fall departure (Sep-Nov)"
            except:
                season_context = "Date parsing failed"
        else:
            season_context = "No specific departure date"
        
        return f"""
You are a destination discovery specialist. Suggest 5-7 destinations based on the traveler's preferences.

TRAVELER PROFILE:
- Desired destination type: {destination_type or "Not specified"}
- Budget: {budget} {budget_currency} {"total" if budget else "Not specified"}
- Travel dates: {departure_date or "Flexible"} ({season_context})
- Duration: {duration} days
- Travelers: {passengers} person(s)
- Nationality: {nationality} (for visa considerations)
- Special requirements: {special_requirements or "None"}

DISCOVERY CRITERIA:
1. Match destination type preferences (beach/mountains/city/cultural/adventure)
2. Consider seasonal weather and tourist patterns
3. Fit budget constraints realistically
4. Account for visa requirements for nationality
5. Suggest appropriate duration for each destination

Return ONLY valid JSON:
{{
    "suggestions": [
        {{
            "destination": "City, Country",
            "country": "Country",
            "reason": "Why this fits their preferences",
            "season_score": 0.0-1.0,
            "budget_fit": "low/medium/high/luxury",
            "highlights": ["main attractions", "key experiences"],
            "best_duration": "X days recommended"
        }}
    ],
    "search_criteria": {{
        "destination_type": "{destination_type}",
        "budget_range": "{budget} {budget_currency}",
        "season": "{season_context}",
        "travelers": {passengers}
    }},
    "confidence_score": 0.0-1.0,
    "seasonality_considered": true
}}

Focus on destinations that are:
- Seasonally appropriate for the travel dates
- Realistically achievable within budget
- Suitable for the group size and nationality
- Aligned with stated preferences
"""
    
    def _parse_response(self, response_text: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
                
            parsed_data = json.loads(response_text)
            
            # Validate and create result
            suggestions = [DestinationSuggestion(**suggestion) for suggestion in parsed_data["suggestions"]]
            
            result = DestinationDiscoveryResult(
                suggestions=suggestions,
                search_criteria=parsed_data.get("search_criteria", {}),
                confidence_score=parsed_data.get("confidence_score", 0.8),
                seasonality_considered=parsed_data.get("seasonality_considered", True)
            )
            
            return result.model_dump()
            
        except Exception as e:
            return self._generate_fallback_suggestions(input_data)
    
    def _generate_fallback_suggestions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic destination suggestions without AI"""
        destination_type = input_data.get("destination_type", "").lower()
        budget = input_data.get("budget", 0)
        
        # Simple rule-based suggestions
        fallback_suggestions = []
        
        if "beach" in destination_type:
            fallback_suggestions = [
                {
                    "destination": "Bali, Indonesia",
                    "country": "Indonesia",
                    "reason": "Popular beach destination with good value",
                    "season_score": 0.8,
                    "budget_fit": "medium",
                    "highlights": ["Beautiful beaches", "Cultural experiences", "Affordable"],
                    "best_duration": "7-10 days"
                },
                {
                    "destination": "Cancun, Mexico",
                    "country": "Mexico",
                    "reason": "Accessible beach destination",
                    "season_score": 0.7,
                    "budget_fit": "medium",
                    "highlights": ["Beach resorts", "Mayan ruins", "Nightlife"],
                    "best_duration": "5-7 days"
                }
            ]
        elif "city" in destination_type:
            fallback_suggestions = [
                {
                    "destination": "Barcelona, Spain",
                    "country": "Spain",
                    "reason": "Vibrant European city with culture",
                    "season_score": 0.7,
                    "budget_fit": "medium",
                    "highlights": ["Architecture", "Museums", "Food scene"],
                    "best_duration": "4-6 days"
                }
            ]
        else:
            # General popular destinations
            fallback_suggestions = [
                {
                    "destination": "Paris, France",
                    "country": "France",
                    "reason": "Classic travel destination",
                    "season_score": 0.6,
                    "budget_fit": "high",
                    "highlights": ["Iconic landmarks", "Art museums", "Cuisine"],
                    "best_duration": "5-7 days"
                }
            ]
        
        fallback_result = {
            "suggestions": fallback_suggestions,
            "search_criteria": {
                "destination_type": destination_type,
                "budget_range": f"{budget} USD" if budget else "Not specified",
                "season": "Year-round",
                "travelers": input_data.get("passengers", 1)
            },
            "confidence_score": 0.4,
            "seasonality_considered": False,
            "mode": "fallback_suggestions"
        }
        
        return self.format_output(fallback_result)