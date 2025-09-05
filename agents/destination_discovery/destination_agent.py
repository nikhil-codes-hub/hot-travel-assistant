import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent
from agents.cache.llm_cache import LLMCache

class DestinationSuggestion(BaseModel):
    destination: str = Field(..., description="Destination name")
    country: str = Field(..., description="Country")
    reason: str = Field(..., description="Why this destination fits")
    season_score: float = Field(..., description="Seasonal suitability 0.0-1.0")
    budget_fit: str = Field(..., description="Budget compatibility: low/medium/high/luxury")
    highlights: List[str] = Field(..., description="Key attractions/experiences")
    best_duration: str = Field(..., description="Recommended stay duration")
    major_attractions: Optional[List[str]] = Field(None, description="Major tourist attractions")
    recommended_activities: Optional[List[str]] = Field(None, description="Recommended activities")
    best_time_to_visit: Optional[str] = Field(None, description="Optimal visiting time")
    approximate_daily_budget: Optional[str] = Field(None, description="Daily budget estimate")
    flight_accessibility: Optional[str] = Field(None, description="Flight connectivity info")
    visa_requirements_hint: Optional[str] = Field(None, description="Visa requirements overview")

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
        
        # Initialize LLM response cache for destination discovery
        cache_dir = os.getenv("LLM_CACHE_DIR", "cache/llm_responses")
        cache_duration = int(os.getenv("LLM_CACHE_DURATION_HOURS", "0"))  # Disabled by default
        self.cache = LLMCache(cache_dir=f"{cache_dir}/destination_discovery", cache_duration_hours=cache_duration)
        
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
        
        # Check cache first for similar destination discovery requests
        cache_key_data = json.dumps(input_data, sort_keys=True)
        cached_response = self.cache.get_cached_response(cache_key_data, {})
        if cached_response:
            self.log(f"✅ Cache hit - returning cached destination suggestions for similar criteria")
            # Add cache hit information to response
            cached_response["cache_info"] = {
                "cache_hit": True,
                "cached_at": cached_response.get("timestamp"),
                "search_criteria": input_data
            }
            return self.format_output(cached_response)
        
        # Force LLM usage - if AI is not available, raise an error instead of fallback
        if not self.ai_available:
            raise Exception("LLM is required for comprehensive destination discovery. Please configure GEMINI_API_KEY or Vertex AI credentials.")
        
        try:
            self.log(f"🔄 Cache miss - calling LLM for destination discovery")
            prompt = self._create_discovery_prompt(input_data)
            
            # Call AI API
            if self.ai_provider == "vertex":
                response = await self._call_vertex_ai(prompt)
            else:
                response = self.model.generate_content(prompt)
            
            # Parse response
            if self.ai_provider == "vertex":
                result = self._parse_response(response, input_data)
            else:
                result = self._parse_response(response.text, input_data)
            
            # Store in cache for future similar requests
            cache_stored = self.cache.store_cached_response(cache_key_data, {}, result)
            if cache_stored:
                self.log(f"💾 Destination discovery response cached for future similar criteria")
            
            # Add cache info to response
            result["cache_info"] = {
                "cache_hit": False,
                "cached": cache_stored,
                "search_criteria": input_data
            }
            
            self.log("✅ AI-powered comprehensive destination planning generated")
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"⚠️ LLM destination discovery failed: {str(e)}")
            raise Exception(f"Comprehensive destination discovery requires LLM: {str(e)}")
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-2.0-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    
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
You are a comprehensive travel planning specialist with expertise in destination discovery, attractions, and comprehensive travel planning. Your role is to provide rich, detailed destination recommendations that enable full travel planning workflows.

TRAVELER PROFILE:
- Desired destination type: {destination_type or "Not specified"}
- Budget: {budget} {budget_currency} {"total" if budget else "Not specified"}
- Travel dates: {departure_date or "Flexible"} ({season_context})
- Duration: {duration} days
- Travelers: {passengers} person(s)
- Nationality: {nationality} (for visa considerations)
- Special requirements: {special_requirements or "None"}

COMPREHENSIVE DISCOVERY MISSION:
1. Suggest 5-7 destinations with rich detail and context
2. Include major attractions, cultural experiences, and activities
3. Consider seasonal weather, local events, and tourist patterns
4. Provide budget-conscious recommendations with cost insights
5. Account for visa requirements and travel logistics
6. Enable full travel planning workflow (flights, hotels, attractions, compliance)

Return ONLY valid JSON with comprehensive travel information:
{{
    "suggestions": [
        {{
            "destination": "City, Country",
            "country": "Country",
            "reason": "Why this fits their preferences with specific benefits",
            "season_score": 0.0-1.0,
            "budget_fit": "low/medium/high/luxury",
            "highlights": ["major attractions", "cultural experiences", "unique activities", "local specialties"],
            "best_duration": "X days recommended",
            "major_attractions": ["Temple complexes", "Museums", "Natural sites", "Cultural districts"],
            "recommended_activities": ["Adventure activities", "Cultural experiences", "Food tours", "Shopping areas"],
            "best_time_to_visit": "Seasonal recommendations and weather patterns",
            "approximate_daily_budget": "Budget range for accommodation, food, activities",
            "flight_accessibility": "Major airports and flight connectivity",
            "visa_requirements_hint": "General visa requirements for the nationality"
        }}
    ],
    "search_criteria": {{
        "destination_type": "{destination_type}",
        "budget_range": "{budget} {budget_currency}",
        "season": "{season_context}",
        "travelers": {passengers}
    }},
    "confidence_score": 0.8-1.0,
    "seasonality_considered": true,
    "comprehensive_planning_enabled": true
}}

COMPREHENSIVE PLANNING FOCUS:
- Provide rich destination context that enables attraction discovery
- Include practical travel information (airports, transportation, costs)
- Consider visa, health, and safety requirements
- Enable seamless transition to flight/hotel search and compliance checking
- Emphasize unique experiences and must-see attractions for each destination
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
            
            parsed_result = result.model_dump()
            self.log(f"✅ Parsed {len(suggestions)} AI destination suggestions successfully")
            return parsed_result
            
        except Exception as e:
            self.log(f"⚠️ AI response parsing failed ({e}), using fallback suggestions")
            fallback_result = self._generate_fallback_suggestions(input_data)
            return fallback_result
    
    def _generate_fallback_suggestions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate context-aware destination suggestions without AI"""
        destination_type = (input_data.get("destination_type") or "").lower()
        budget = input_data.get("budget", 0)
        departure_date = input_data.get("departure_date")
        duration = input_data.get("duration", 7)
        
        # Get season context for departure date
        season = "winter"
        if departure_date:
            try:
                dep_date = datetime.fromisoformat(departure_date)
                month = dep_date.month
                if month in [3, 4, 5]:
                    season = "spring"
                elif month in [6, 7, 8]:
                    season = "summer"
                elif month in [9, 10, 11]:
                    season = "fall"
            except:
                pass
        
        # Context-aware suggestions based on request patterns
        fallback_suggestions = []
        
        # Check for snowy/winter destination requests
        context_info = f"{destination_type} {input_data}"
        if any(pattern in context_info.lower() for pattern in ["snowy", "snow", "ski", "winter", "cold", "mountain"]):
            self.log("🏔️ Providing snowy destination suggestions for winter travel")
            fallback_suggestions = [
                {
                    "destination": "Zermatt, Switzerland",
                    "country": "Switzerland",
                    "reason": "World-famous Alpine resort with guaranteed snow and Matterhorn views",
                    "season_score": 0.95,
                    "budget_fit": "luxury" if budget > 2000 else "high",
                    "highlights": ["Matterhorn views", "Year-round skiing", "Luxury Alpine experience", "Car-free village"],
                    "best_duration": "6-8 days"
                },
                {
                    "destination": "Aspen, Colorado",
                    "country": "USA", 
                    "reason": "Premium ski destination with excellent November conditions",
                    "season_score": 0.9,
                    "budget_fit": "high",
                    "highlights": ["World-class skiing", "Luxury amenities", "Mountain dining", "Apres-ski culture"],
                    "best_duration": "5-7 days"
                },
                {
                    "destination": "Whistler, British Columbia",
                    "country": "Canada",
                    "reason": "Olympic ski resort with reliable early season snow",
                    "season_score": 0.85,
                    "budget_fit": "medium",
                    "highlights": ["2010 Olympics venue", "Village atmosphere", "Dual mountain skiing", "Canadian hospitality"],
                    "best_duration": "6-8 days"
                }
            ]
        elif "beach" in destination_type or any(pattern in context_info.lower() for pattern in ["warm", "tropical", "beach"]):
            fallback_suggestions = [
                {
                    "destination": "Bali, Indonesia",
                    "country": "Indonesia",
                    "reason": "Popular beach destination with good value and cultural richness",
                    "season_score": 0.8,
                    "budget_fit": "medium",
                    "highlights": ["Beautiful beaches", "Cultural experiences", "Affordable luxury", "Temples"],
                    "best_duration": "7-10 days"
                },
                {
                    "destination": "Maldives",
                    "country": "Maldives",
                    "reason": "Ultimate tropical paradise with overwater villas",
                    "season_score": 0.9,
                    "budget_fit": "luxury",
                    "highlights": ["Overwater bungalows", "Crystal clear waters", "World-class diving", "Complete relaxation"],
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
            "confidence_score": 0.7,  # Higher confidence for curated suggestions
            "seasonality_considered": False,
            "mode": "fallback_suggestions"
        }
        
        self.log(f"✅ Generated {len(fallback_suggestions)} fallback destination suggestions")
        return fallback_result