import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent
from agents.cache.llm_cache import LLMCache

class EventDetails(BaseModel):
    event_id: str = Field(..., description="Event ID")
    name: str = Field(..., description="Event name")
    event_type: str = Field(..., description="Event type (festival, concert, sports, cultural, etc.)")
    description: Optional[str] = Field(None, description="Event description")
    location: str = Field(..., description="Event location")
    city: str = Field(..., description="Specific city where event takes place")
    country: Optional[str] = Field(None, description="Country where event takes place")
    venue: Optional[str] = Field(None, description="Specific venue")
    start_date: str = Field(..., description="Event start date")
    end_date: Optional[str] = Field(None, description="Event end date")
    duration: Optional[str] = Field(None, description="Event duration")
    schedule: Optional[List[Dict[str, Any]]] = Field(None, description="Daily schedule")
    ticket_info: Optional[Dict[str, Any]] = Field(None, description="Ticket information")
    accessibility: Optional[Dict[str, Any]] = Field(None, description="Accessibility information")
    weather_considerations: Optional[str] = Field(None, description="Weather to expect")
    what_to_bring: Optional[List[str]] = Field(None, description="What to bring")
    cultural_significance: Optional[str] = Field(None, description="Cultural significance")

class EventSearchResult(BaseModel):
    events: List[EventDetails]
    search_criteria: Dict[str, Any]
    destination_context: Dict[str, Any]
    travel_recommendations: Dict[str, Any]
    confidence_score: float

class EventSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("EventSearchAgent")
        self.ai_provider = os.getenv("AI_PROVIDER", "gemini")
        self.ai_available = False
        
        # Initialize LLM response cache for event search
        cache_dir = os.getenv("LLM_CACHE_DIR", "cache/llm_responses")
        cache_duration = int(os.getenv("LLM_CACHE_DURATION_HOURS", "0"))  # Disabled by default
        self.cache = LLMCache(cache_dir=f"{cache_dir}/event_search", cache_duration_hours=cache_duration)
        
        try:
            if self.ai_provider == "vertex":
                # Initialize Vertex AI
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("VERTEX_AI_LOCATION")
                if project_id and location:
                    aiplatform.init(project=project_id, location=location)
                    self.model = None
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
        Search for events and festivals based on criteria
        
        Input:
        - event_name: specific event name
        - event_type: type of event  
        - destination: location for events
        - date_range: when to search for events
        - duration: trip duration for planning
        - preferences: cultural, music, food, etc.
        """
        self.validate_input(input_data, [])
        
        # Check cache first
        cache_key_data = json.dumps(input_data, sort_keys=True)
        cached_response = self.cache.get_cached_response(cache_key_data, {})
        if cached_response:
            self.log(f"✅ Cache hit - returning cached event information")
            cached_response["cache_info"] = {
                "cache_hit": True,
                "cached_at": cached_response.get("timestamp"),
                "search_criteria": input_data
            }
            return self.format_output(cached_response)
        
        # Force LLM usage for comprehensive event information
        if not self.ai_available:
            self.log("⚠️ LLM not available - using fallback event information")
            return self._generate_fallback_events(input_data)
        
        try:
            self.log(f"🔄 Cache miss - calling LLM for event search")
            prompt = self._create_event_search_prompt(input_data)
            
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
            
            # Store in cache
            cache_stored = self.cache.store_cached_response(cache_key_data, {}, result)
            if cache_stored:
                self.log(f"💾 Event search response cached")
            
            # Add cache info to response
            result["cache_info"] = {
                "cache_hit": False,
                "cached": cache_stored,
                "search_criteria": input_data
            }
            
            self.log("✅ AI-powered event search completed")
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"⚠️ LLM event search failed: {str(e)}")
            return self._generate_fallback_events(input_data)
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-2.0-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    
    def _create_event_search_prompt(self, input_data: Dict[str, Any]) -> str:
        event_name = input_data.get("event_name")
        event_type = input_data.get("event_type")
        destination = input_data.get("destination")
        date_range = input_data.get("date_range")
        duration = input_data.get("duration", 7)
        preferences = input_data.get("preferences", [])
        
        return f"""
You are a comprehensive event and festival research specialist with expertise in cultural events, festivals, concerts, and special celebrations worldwide. Your mission is to provide detailed, accurate information about events that enables complete travel planning.

EVENT SEARCH CRITERIA:
- Event name: {event_name or "Not specified"}
- Event type: {event_type or "Not specified"}
- Destination: {destination or "Not specified"}
- Date range: {date_range or "Flexible"}
- Trip duration: {duration} days
- Preferences: {preferences or "None specified"}

COMPREHENSIVE EVENT RESEARCH MISSION:
1. Find detailed information about the requested event(s)
2. Provide practical travel planning information
3. Include cultural context and significance
4. Suggest optimal timing and duration for the experience
5. Include logistics, accessibility, and practical considerations
6. Enable seamless travel planning integration

Return ONLY valid JSON with comprehensive event information:
{{
    "events": [
        {{
            "event_id": "unique_identifier",
            "name": "Full event name",
            "event_type": "festival/concert/sports/cultural/religious/seasonal",
            "description": "Detailed description of the event, its significance, and what to expect",
            "location": "City, Country",
            "city": "Specific city where event takes place",
            "country": "Country where event takes place",
            "venue": "Specific venue or area where event takes place",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD (if multi-day event)",
            "duration": "Duration description (3 days, 1 week, etc.)",
            "schedule": [
                {{
                    "date": "YYYY-MM-DD",
                    "time": "HH:MM",
                    "activity": "Main activities for this time",
                    "highlights": ["key moments", "must-see elements"]
                }}
            ],
            "ticket_info": {{
                "required": true/false,
                "advance_booking": "How far in advance to book",
                "price_range": "Typical ticket costs",
                "where_to_buy": "Official sources"
            }},
            "accessibility": {{
                "wheelchair_accessible": true/false,
                "crowd_level": "high/medium/low",
                "family_friendly": true/false,
                "age_restrictions": "Any age restrictions"
            }},
            "weather_considerations": "Expected weather and how it affects the event",
            "what_to_bring": ["essential items", "recommended items", "cultural considerations"],
            "cultural_significance": "Historical background and cultural importance"
        }}
    ],
    "search_criteria": {{
        "event_name": "{event_name}",
        "destination": "{destination}",
        "event_type": "{event_type}",
        "date_preference": "{date_range}"
    }},
    "destination_context": {{
        "country": "Country name",
        "best_airports": ["nearest airports for travel"],
        "local_transportation": "How to get to event from airport/hotels",
        "recommended_areas": ["best areas to stay for event access"],
        "local_customs": "Important cultural considerations for visitors"
    }},
    "travel_recommendations": {{
        "optimal_duration": "{duration} days recommended for full experience",
        "best_arrival_time": "When to arrive before event",
        "accommodation_booking": "How far in advance to book hotels",
        "additional_attractions": ["other things to see while there"],
        "travel_tips": ["practical advice for event attendance"]
    }},
    "confidence_score": 0.8-1.0
}}

CRITICAL REQUIREMENTS:
- Provide accurate, current information about real events
- Include practical planning information for travelers
- Consider seasonal timing and local conditions  
- Enable seamless integration with flight/hotel search
- Include cultural sensitivity and etiquette guidance
- For popular events like festivals, include crowd management and booking advice

SPECIFIC EVENT KNOWLEDGE:
- Water Lantern Festival: Beautiful evening event with floating lanterns, typically held in various locations including Thailand, very photogenic and peaceful
- Oktoberfest: Munich's famous beer festival, September-October, requires advance planning
- Cherry Blossom festivals: Spring events in Japan, Korea, Washington DC
- Cultural festivals: Religious and cultural celebrations, celebrated globally
- Cultural festivals often have deep spiritual/historical significance
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
            events = [EventDetails(**event) for event in parsed_data["events"]]
            
            result = EventSearchResult(
                events=events,
                search_criteria=parsed_data.get("search_criteria", {}),
                destination_context=parsed_data.get("destination_context", {}),
                travel_recommendations=parsed_data.get("travel_recommendations", {}),
                confidence_score=parsed_data.get("confidence_score", 0.8)
            )
            
            parsed_result = result.model_dump()
            self.log(f"✅ Parsed {len(events)} AI event results successfully")
            return parsed_result
            
        except Exception as e:
            self.log(f"⚠️ AI response parsing failed ({e}), using fallback events")
            return self._generate_fallback_events(input_data)
    
    def _generate_fallback_events(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback event information without AI"""
        event_name = input_data.get("event_name", "").lower()
        destination = input_data.get("destination", "").lower()
        event_type = input_data.get("event_type", "").lower()
        
        fallback_events = []
        
        # Water Lantern Festival
        if "water lantern" in event_name or ("water" in event_name and "lantern" in event_name):
            fallback_events.append({
                "event_id": "water_lantern_festival_thailand",
                "name": "Water Lantern Festival",
                "event_type": "festival",
                "description": "Beautiful evening festival where participants release floating lanterns on water, creating a magical atmosphere. A peaceful, spiritual experience often associated with making wishes and letting go.",
                "location": "Thailand (Chiang Mai, Bangkok)",
                "city": "Chiang Mai",
                "country": "Thailand",
                "venue": "Various lakes, rivers, and designated water bodies",
                "start_date": "2025-11-15",  # Typical timing
                "end_date": "2025-11-15",
                "duration": "1 evening (3-4 hours)",
                "schedule": [
                    {
                        "date": "2025-11-15",
                        "time": "18:00",
                        "activity": "Festival setup and registration",
                        "highlights": ["Cultural performances", "Food stalls", "Lantern preparation"]
                    },
                    {
                        "date": "2025-11-15", 
                        "time": "19:30",
                        "activity": "Lantern release ceremony",
                        "highlights": ["Mass lantern release", "Photography opportunities", "Spiritual ceremony"]
                    }
                ],
                "ticket_info": {
                    "required": True,
                    "advance_booking": "1-2 months in advance",
                    "price_range": "$25-50 USD per person",
                    "where_to_buy": "Official event websites, local tour operators"
                },
                "accessibility": {
                    "wheelchair_accessible": True,
                    "crowd_level": "high",
                    "family_friendly": True,
                    "age_restrictions": "None"
                },
                "weather_considerations": "Evening event, can be cool. Bring light jacket. Events may be cancelled due to rain or strong winds.",
                "what_to_bring": ["Camera", "Light jacket", "Closed-toe shoes", "Small bag", "Respect for ceremony"],
                "cultural_significance": "Represents letting go of negative thoughts and making wishes for the future. Often connected to Buddhist and Hindu traditions of light festivals."
            })
        
        
        # Oktoberfest
        elif "oktoberfest" in event_name:
            fallback_events.append({
                "event_id": "oktoberfest_munich",
                "name": "Oktoberfest",
                "event_type": "festival",
                "description": "The world's largest beer festival and traveling funfair, featuring traditional Bavarian culture, beer, food, and music.",
                "location": "Munich, Germany",
                "city": "Munich",
                "country": "Germany",
                "venue": "Theresienwiese",
                "start_date": "2025-09-20",
                "end_date": "2025-10-05",
                "duration": "16 days",
                "schedule": [
                    {
                        "date": "2025-09-20",
                        "time": "12:00",
                        "activity": "Opening ceremony",
                        "highlights": ["Mayor taps first keg", "Traditional parade", "Live music"]
                    }
                ],
                "ticket_info": {
                    "required": False,
                    "advance_booking": "Table reservations recommended 2-3 months ahead",
                    "price_range": "Free entry, €10-15 per beer",
                    "where_to_buy": "Official Oktoberfest website for table reservations"
                },
                "accessibility": {
                    "wheelchair_accessible": True,
                    "crowd_level": "very high",
                    "family_friendly": True,
                    "age_restrictions": "18+ for alcohol"
                },
                "weather_considerations": "September-October weather can be unpredictable. Dress in layers.",
                "what_to_bring": ["Traditional clothing (optional)", "Cash", "Patience for crowds"],
                "cultural_significance": "Celebrates Bavarian culture and tradition, originally a royal wedding celebration from 1810."
            })
        
        # Generic fallback based on destination
        elif destination:
            # Extract city and country from destination
            destination_parts = destination.split(',')
            destination_city = destination_parts[0].strip()
            destination_country = destination_parts[-1].strip() if len(destination_parts) > 1 else destination_city
            
            fallback_events.append({
                "event_id": f"generic_event_{destination.replace(' ', '_')}",
                "name": f"Cultural Events in {destination.title()}",
                "event_type": "cultural",
                "description": f"Various cultural events and festivals typically held in {destination.title()}",
                "location": destination.title(),
                "city": destination_city.title(),
                "country": destination_country.title(),
                "venue": "Various venues",
                "start_date": "2025-12-01",
                "end_date": "2025-12-01", 
                "duration": "Varies",
                "cultural_significance": f"Local cultural celebrations and events in {destination.title()}"
            })
        
        # Default fallback
        if not fallback_events:
            fallback_events.append({
                "event_id": "generic_festival",
                "name": "Local Festivals and Events",
                "event_type": "festival",
                "description": "Various local festivals and cultural events",
                "location": "Multiple locations",
                "city": "Bangkok",
                "country": "Thailand",
                "venue": "Various venues",
                "start_date": "2025-12-01",
                "end_date": "2025-12-01",
                "duration": "Varies",
                "cultural_significance": "Local cultural celebrations"
            })
        
        fallback_result = {
            "events": fallback_events,
            "search_criteria": {
                "event_name": input_data.get("event_name"),
                "destination": input_data.get("destination"),
                "event_type": input_data.get("event_type")
            },
            "destination_context": {
                "country": destination.split(',')[-1].strip() if ',' in destination else destination,
                "best_airports": ["Major international airports"],
                "local_transportation": "Taxis, public transport, ride-sharing",
                "recommended_areas": ["City center", "Near event venues"],
                "local_customs": "Respect local customs and traditions"
            },
            "travel_recommendations": {
                "optimal_duration": "5-7 days recommended",
                "best_arrival_time": "1-2 days before event",
                "accommodation_booking": "Book 2-3 months in advance for popular events",
                "additional_attractions": ["Local attractions", "Cultural sites"],
                "travel_tips": ["Book early", "Check weather", "Respect local customs"]
            },
            "confidence_score": 0.7,
            "mode": "fallback_events"
        }
        
        self.log(f"✅ Generated {len(fallback_events)} fallback event suggestions")
        return fallback_result