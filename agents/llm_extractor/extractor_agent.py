import os
from typing import Dict, Any, List, Optional
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent
from agents.cache.llm_cache import LLMCache

class TravelRequirements(BaseModel):
    destination: Optional[str] = Field(None, description="Specific destination if mentioned")
    destination_type: Optional[str] = Field(None, description="Type of destination (beach, mountains, city, etc.)")
    event_name: Optional[str] = Field(None, description="Specific event or festival name if mentioned")
    event_type: Optional[str] = Field(None, description="Type of event (festival, concert, sports, cultural, etc.)")
    departure_date: Optional[str] = Field(None, description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(None, description="Return date in YYYY-MM-DD format")
    duration: Optional[int] = Field(None, description="Trip duration in days")
    budget: Optional[float] = Field(None, description="Budget amount")
    budget_currency: Optional[str] = Field("USD", description="Budget currency")
    passengers: int = Field(1, description="Number of passengers")
    children: Optional[int] = Field(None, description="Number of children")
    travel_class: Optional[str] = Field(None, description="Preferred travel class")
    accommodation_type: Optional[str] = Field(None, description="Preferred accommodation type")
    special_requirements: Optional[List[str]] = Field(None, description="Special requirements or preferences")
    
class ExtractionResult(BaseModel):
    requirements: TravelRequirements
    missing_fields: List[str]
    confidence_score: float
    original_request: str

class LLMExtractorAgent(BaseAgent):
    def __init__(self):
        super().__init__("LLMExtractorAgent")
        self.ai_provider = "vertex"  # Only using Vertex AI
        self.ai_available = False
        
        # Initialize LLM response cache
        cache_dir = os.getenv("LLM_CACHE_DIR", "cache/llm_responses")
        cache_duration = int(os.getenv("LLM_CACHE_DURATION_HOURS", "0"))  # Disabled by default
        self.cache = LLMCache(cache_dir=cache_dir, cache_duration_hours=cache_duration)
        
        try:
            self.log("🔧 Initializing Vertex AI")
            
            # Initialize Vertex AI
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            
            if not project_id:
                self.log("❌ GOOGLE_CLOUD_PROJECT not set - Vertex AI unavailable")
                self.log("💡 Please set GOOGLE_CLOUD_PROJECT in your .env file")
            else:
                self.log(f"🔄 Connecting to Vertex AI: project={project_id}, location={location}")
                aiplatform.init(project=project_id, location=location)
                self.model = None  # Will use aiplatform.gapic.PredictionServiceClient
                self.ai_available = True
                self.log("✅ Vertex AI successfully initialized")
                    
        except Exception as e:
            self.log(f"❌ Vertex AI initialization failed: {str(e)}")
            self.log("⚠️  Falling back to pattern-based extraction (limited destination coverage)")
            self.ai_available = False
            self.model = None
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        self.validate_input(input_data, ["user_request"])
        
        user_request = input_data["user_request"]
        conversation_context = input_data.get("conversation_context", {})
        
        # CRITICAL: Remove any PII before sending to LLM or using for cache
        sanitized_request = self._sanitize_pii(user_request)
        sanitized_context = self._sanitize_conversation_context(conversation_context)
        
        # Check cache first before making LLM call
        cached_response = self.cache.get_cached_response(sanitized_request, sanitized_context)
        if cached_response:
            self.log(f"✅ Cache hit - returning cached travel planning data for similar request")
            # Add cache hit information to response
            cached_response["cache_info"] = {
                "cache_hit": True,
                "cached_at": cached_response.get("timestamp"),
                "original_request": user_request
            }
            return self.format_output(cached_response)
        
        # Check if AI is available - now enforcing LLM usage
        if not self.ai_available:
            self.log("⚠️  LLM not available - this limits destination coverage to hardcoded patterns")
            self.log("🔧  Please configure GEMINI_API_KEY in .env file for comprehensive destination extraction")
            return self._generate_fallback_extraction(user_request, conversation_context)
        
        try:
            self.log(f"🔄 Cache miss - calling LLM for travel planning extraction")
            
            # Create extraction prompt with sanitized data
            prompt = self._create_extraction_prompt(sanitized_request, sanitized_context)
            
            # Call AI API
            if self.ai_provider == "vertex":
                response = await self._call_vertex_ai(prompt)
            else:
                response = self.model.generate_content(prompt)
            
            # Parse response
            if self.ai_provider == "vertex":
                extracted_data = self._parse_response(response, sanitized_request, sanitized_context)
            else:
                extracted_data = self._parse_response(response.text, sanitized_request, sanitized_context)
            
            # Store in cache for future similar requests
            cache_stored = self.cache.store_cached_response(sanitized_request, sanitized_context, extracted_data)
            if cache_stored:
                self.log(f"💾 LLM response cached successfully for future similar requests")
            
            # Add cache info to response
            extracted_data["cache_info"] = {
                "cache_hit": False,
                "cached": cache_stored,
                "original_request": user_request
            }
            
            return self.format_output(extracted_data)
        except Exception as e:
            self.log(f"⚠️  LLM extraction failed: {str(e)} - using intelligent defaults")
            return self._generate_fallback_extraction(user_request, conversation_context)
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-2.0-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    
    def _sanitize_pii(self, user_request: str) -> str:
        """Remove PII information from user request before sending to LLM"""
        import re
        
        if not user_request:
            return user_request
            
        # Remove email addresses
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', user_request)
        
        # Remove phone numbers (various formats)
        sanitized = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[PHONE]', sanitized)
        sanitized = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', sanitized)
        
        # Remove passport numbers (basic pattern)
        sanitized = re.sub(r'\b[A-Z]{1,2}\d{6,9}\b', '[PASSPORT]', sanitized)
        
        # Remove credit card numbers (basic pattern)
        sanitized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', sanitized)
        
        # Remove SSN patterns
        sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', sanitized)
        
        return sanitized
    
    def _sanitize_conversation_context(self, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove PII from conversation context before sending to LLM"""
        if not conversation_context:
            return conversation_context
            
        # Create a clean copy without PII fields
        sanitized_context = {}
        
        # Only include travel planning fields, exclude PII
        safe_fields = [
            'destination', 'departure_date', 'return_date', 'duration', 
            'budget', 'budget_currency', 'passengers', 'children',
            'travel_class', 'accommodation_type', 'special_requirements', 'destination_type'
        ]
        
        for field in safe_fields:
            if field in conversation_context:
                sanitized_context[field] = conversation_context[field]
                
        return sanitized_context
    
    def _create_extraction_prompt(self, user_request: str, conversation_context: Dict[str, Any] = None) -> str:
        from datetime import datetime, timedelta
        
        # Get today's date and 30 days from now for reference
        today = datetime.now()
        thirty_days_later = today + timedelta(days=30)
        today_str = today.strftime("%Y-%m-%d")
        thirty_days_str = thirty_days_later.strftime("%Y-%m-%d")
        current_year = today.year
        
        context_info = ""
        if conversation_context:
            context_info = f"""

PREVIOUS CONVERSATION CONTEXT:
{conversation_context}

IMPORTANT: If the user request provides new information that wasn't in the previous context, update those fields. If the user request doesn't mention a field that exists in the previous context, keep the previous value."""

        return f"""
You are an expert travel planning assistant specializing in comprehensive travel requirements extraction and destination insights. Your role is to extract travel requirements AND provide rich travel planning context for any destination mentioned.

CORE MISSION:
- Extract explicit travel requirements from user requests
- For ANY destination mentioned (even vague ones), provide comprehensive travel planning context
- Extract EVENT-based travel requirements (festivals, concerts, cultural events, sports)
- Enable full travel planning workflow including attractions, flights, hotels, visa requirements, health advisories
- Handle both specific destinations (Thailand, Paris), vague requests (somewhere warm, tropical place), and EVENT-BASED requests (Water Lantern Festival in Thailand, Oktoberfest in Munich)

DESTINATION EXTRACTION RULES:
- For "Bangkok" queries, ALWAYS extract destination as "Bangkok, Thailand" (not just "Bangkok")
- For "Thailand" queries, ALWAYS extract as "Bangkok, Thailand" since Bangkok is the main international gateway
- For city names, include country when internationally known (e.g., "Paris, France", "Tokyo, Japan", "London, UK")
- Use standardized city names that match international airport/hotel booking systems

CRITICAL RULES:
1. Extract all explicitly mentioned travel information including EVENTS and FESTIVALS
2. For destinations (specific OR vague) AND EVENTS: Always enable comprehensive planning
3. EVENT DETECTION: Look for patterns like "festival", "concert", "event", "celebration", specific event names
4. Apply INTELLIGENT DEFAULTS for missing parameters to enable comprehensive planning:
   - Duration: Suggest appropriate length based on destination/event (7 days international, 4-5 domestic, extend for festivals)
   - Passengers: Default to 2 people for better travel experience
   - Budget: Suggest realistic range based on destination and duration
   - Travel Class: Default to economy for budget planning
5. MINIMIZE missing_fields - only mark as missing if absolutely critical and cannot be defaulted
6. EVENT-based requests like 'Water Lantern Festival in Thailand' should trigger full travel planning workflow
7. Never mark destination as missing if ANY location hint is provided (including events in locations)
8. If conversation context exists, merge new information with existing context{context_info}

CURRENT DATE INFORMATION:
- Today's date: {today_str}
- Default departure date (30 days from today): {thirty_days_str}

User Request: "{user_request}"

Extract the following information and return ONLY valid JSON with intelligent defaults:
{{
    "requirements": {{
        "destination": "Always extract if any location is mentioned - specific ('Bangkok, Thailand', 'Paris, France') or vague ('somewhere tropical', 'beach destination', 'Europe'). Extract from event context if mentioned (Water Lantern Festival in Thailand -> Bangkok, Thailand). IMPORTANT: For Bangkok queries, always use 'Bangkok, Thailand'. Only null if absolutely no location mentioned",
        "destination_type": "Infer from context: beach/mountains/city/adventure/cultural/romantic/tropical/ski/festival/event/etc",
        "event_name": "Extract specific event/festival name if mentioned (Water Lantern Festival, Oktoberfest, Diwali celebration, etc.)",
        "event_type": "Classify event type if mentioned: festival/concert/sports/cultural/religious/seasonal/etc",
        "departure_date": "YYYY-MM-DD if specific date mentioned. Examples: '15th Sep' -> '2025-09-15', 'September 15' -> '2025-09-15', 'Sep 15 2025' -> '2025-09-15'. If no year specified, assume current year ({current_year}). IMPORTANT: For event-based travel (festivals like Diwali, Oktoberfest, etc.), use 'EVENT_BASED' as placeholder - the system will calculate optimal arrival timing based on event dates. Use approximate dates for relative terms ('next month' -> '2025-12-01'), or use {thirty_days_str} if no date specified.",
        "return_date": "YYYY-MM-DD if return date specified, calculate based on duration if available",
        "duration": "Extract if mentioned, OR suggest intelligent default: 7 days for international, 4-5 days for domestic/city breaks, 10-14 days for Asia/distant destinations, extend for festivals (5-8 days for festival experience)",
        "budget": "Extract if currency mentioned, OR suggest reasonable range based on destination (e.g., 1500-3000 for Thailand, 2000-4000 for Europe per person for 7 days). Add festival premium if event-based",
        "budget_currency": "currency code if specified, 'USD' as default",
        "passengers": "Extract if mentioned, default to 2 people for better travel experience and planning",
        "children": "number of children if explicitly mentioned, null otherwise",
        "travel_class": "economy/premium_economy/business/first if mentioned, 'economy' as default for budget planning",
        "accommodation_type": "hotel/resort/hostel/apartment/bnb if mentioned, suggest based on destination and inferred budget. Consider festival proximity if event-based",
        "special_requirements": ["explicit requirements or inferred from destination/context/events"]
    }},
    "suggested_defaults": {{
        "duration_reasoning": "Why this duration makes sense for the destination",
        "budget_reasoning": "Budget estimate explanation and what it covers",
        "passenger_assumption": "Why defaulting to this number of passengers",
        "recommended_travel_class": "Suggested class based on budget and destination"
    }},
    "missing_fields": ["list ONLY truly critical fields that cannot be reasonably defaulted - minimize this list"],
    "confidence_score": "0.8-1.0 for comprehensive planning with intelligent defaults",
    "planning_context": {{
        "requires_comprehensive_planning": true,
        "destination_specificity": "specific/vague/general",
        "defaults_applied": true,
        "recommended_workflow": ["destination_discovery", "attractions", "flights", "hotels", "visa_requirements", "health_advisory"]
    }}
}}

COMPREHENSIVE PLANNING ENABLEMENT:
- ANY destination mention should enable full travel planning workflow
- Apply intelligent defaults for duration, passengers, budget to minimize missing fields
- NEVER block comprehensive planning due to missing basic parameters that can be defaulted
- For vague destinations, still extract what's available and let destination discovery handle specifics
- Goal: Enable attractions research, flight/hotel search, visa requirements, health advisories for ALL queries
- Even minimal input like "I want to visit Thailand" should result in comprehensive travel planning

INTELLIGENT DEFAULTS EXAMPLES:
- "Thailand trip" → Duration: 7-10 days, Passengers: 2, Budget: $2000-3000 per person
- "Paris vacation" → Duration: 5 days, Passengers: 2, Budget: $2500-3500 per person
- "Beach destination" → Duration: 7 days, Passengers: 2, Budget: varies by destination suggestion
"""
    
    def _parse_response(self, response_text: str, original_request: str) -> Dict[str, Any]:
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
                
            parsed_data = json.loads(response_text)
            
            # Validate and create result
            requirements = TravelRequirements(**parsed_data["requirements"])
            
            result = ExtractionResult(
                requirements=requirements,
                missing_fields=parsed_data.get("missing_fields", []),
                confidence_score=parsed_data.get("confidence_score", 0.8),
                original_request=original_request
            )
            
            # Add planning context and suggested defaults if available
            result_dict = result.model_dump()
            if "planning_context" in parsed_data:
                result_dict["planning_context"] = parsed_data["planning_context"]
            if "suggested_defaults" in parsed_data:
                result_dict["suggested_defaults"] = parsed_data["suggested_defaults"]
            
            return result_dict
            
        except Exception as e:
            # Apply intelligent defaults even in error scenarios
            default_requirements = TravelRequirements(
                passengers=2,  # Default to 2 people for better travel experience
                duration=7,    # Default to 7 days for international travel
                travel_class="business",  # Default to business for premium experience
                budget_currency="USD"
            )
            requirements_dict = default_requirements.model_dump()
            
            # Try to extract basic destination from original request
            user_lower = original_request.lower()
            if "thailand" in user_lower or "bangkok" in user_lower:
                requirements_dict["destination"] = "Bangkok, Thailand"
                requirements_dict["budget"] = 2000  # Reasonable Thailand budget for 2 people
                requirements_dict["destination_type"] = "tropical"
            elif "bangalore" in user_lower or "bengaluru" in user_lower:
                requirements_dict["destination"] = "Bangalore, India"
                requirements_dict["budget"] = 1500  # Indian city budget
                requirements_dict["duration"] = 4  # City break duration
                requirements_dict["destination_type"] = "city"
            elif any(city in user_lower for city in ["mumbai", "bombay", "delhi", "chennai", "hyderabad", "kolkata"]):
                if "mumbai" in user_lower or "bombay" in user_lower:
                    requirements_dict["destination"] = "Mumbai, India"
                elif "delhi" in user_lower:
                    requirements_dict["destination"] = "Delhi, India"
                elif "chennai" in user_lower:
                    requirements_dict["destination"] = "Chennai, India"
                elif "hyderabad" in user_lower:
                    requirements_dict["destination"] = "Hyderabad, India"
                elif "kolkata" in user_lower:
                    requirements_dict["destination"] = "Kolkata, India"
                requirements_dict["budget"] = 1500  # Indian city budget
                requirements_dict["duration"] = 4
                requirements_dict["destination_type"] = "city"
            elif "paris" in user_lower:
                requirements_dict["destination"] = "Paris"
                requirements_dict["duration"] = 5  # City break duration
                requirements_dict["budget"] = 3500  # Expensive European city
            elif "tokyo" in user_lower or "japan" in user_lower:
                requirements_dict["destination"] = "Tokyo, Japan"
                requirements_dict["duration"] = 5  # City break duration
                requirements_dict["budget"] = 3000  # Japanese city budget
                requirements_dict["destination_type"] = "city"
            elif any(pattern in user_lower for pattern in ["beach", "tropical", "warm"]):
                requirements_dict["destination"] = "tropical beach destination"
                requirements_dict["destination_type"] = "beach"
                requirements_dict["budget"] = 2500
            
            # Set default budget if none was assigned
            if not requirements_dict.get("budget"):
                requirements_dict["budget"] = 3000  # Default international budget
            
            # Minimize missing fields - only mark truly critical ones as missing
            missing_fields = []
            if not requirements_dict.get("destination"):
                missing_fields.append("destination")
            # Don't mark duration, passengers, or budget as missing since we have defaults
            
            return {
                "requirements": requirements_dict,
                "missing_fields": missing_fields,
                "confidence_score": 0.6,  # Higher confidence with intelligent defaults
                "original_request": original_request,
                "suggested_defaults": {
                    "duration_reasoning": "Applied 7-day default for international travel or 5 days for city breaks",
                    "budget_reasoning": "Estimated based on destination and duration for 2 people",
                    "passenger_assumption": "Defaulted to 2 people for optimal travel experience",
                    "recommended_travel_class": "Business class for premium travel experience"
                },
                "planning_context": {
                    "requires_comprehensive_planning": True,
                    "defaults_applied": True,
                    "destination_specificity": "extracted" if requirements_dict.get("destination") else "missing"
                },
                "parsing_error": str(e)
            }
    
    def _generate_fallback_extraction(self, user_request: str, conversation_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a basic extraction without AI and determine missing fields dynamically"""
        # Start with conversation context if available
        if conversation_context is None:
            conversation_context = {}
            
        # Initialize with previous values from conversation context
        destination = conversation_context.get("destination")
        duration = conversation_context.get("duration")
        departure_date = conversation_context.get("departure_date")
        budget = conversation_context.get("budget")
        travel_class = conversation_context.get("travel_class")
        passengers = conversation_context.get("passengers", 1)
        
        user_lower = user_request.lower()
        
        # Initialize event tracking
        event_name = conversation_context.get("event_name")
        event_type = conversation_context.get("event_type")
        
        # Extract event information first (events often contain destination info)
        import re
        
        # Check for specific festivals/events
        if "water lantern festival" in user_lower or "lantern festival" in user_lower or ("lantern" in user_lower and ("event" in user_lower or "festival" in user_lower)):
            event_name = "Water Lantern Festival"
            event_type = "festival"
            if "thailand" in user_lower:
                destination = "Thailand"
        elif "oktoberfest" in user_lower:
            event_name = "Oktoberfest"
            event_type = "festival"
            if "munich" in user_lower or "germany" in user_lower:
                destination = "Munich, Germany"
        elif "holi" in user_lower and ("festival" in user_lower or "celebration" in user_lower):
            event_name = "Holi Festival"
            event_type = "cultural"
            if not destination and "india" in user_lower:
                destination = "India"
        elif "cherry blossom" in user_lower and ("festival" in user_lower or "season" in user_lower):
            event_name = "Cherry Blossom Festival"
            event_type = "seasonal"
            if not destination and "japan" in user_lower:
                destination = "Japan"
        # Generic event/festival patterns
        elif re.search(r'(\w+(?:\s+\w+)*)\s+festival', user_lower):
            match = re.search(r'(\w+(?:\s+\w+)*)\s+festival', user_lower)
            event_name = f"{match.group(1).title()} Festival"
            event_type = "festival"
        elif re.search(r'(\w+(?:\s+\w+)*)\s+concert', user_lower):
            match = re.search(r'(\w+(?:\s+\w+)*)\s+concert', user_lower)
            event_name = f"{match.group(1).title()} Concert"
            event_type = "concert"
        elif re.search(r'(\w+(?:\s+\w+)*)\s+event', user_lower):
            match = re.search(r'(\w+(?:\s+\w+)*)\s+event', user_lower)
            event_name = f"{match.group(1).title()} Event"
            event_type = "event"
        
        # Extract destination (only override if new one is found)
        # First check for vague destination patterns
        if "somewhere snowy" in user_lower or "snowy place" in user_lower:
            destination = "somewhere snowy"
        elif "somewhere warm" in user_lower or "warm place" in user_lower:
            destination = "somewhere warm" 
        elif "somewhere tropical" in user_lower or "tropical place" in user_lower:
            destination = "somewhere tropical"
        elif any(beach_term in user_lower for beach_term in ["beach", "beaches", "beach side", "beachside", "beach destination", "seaside", "coastal"]):
            destination = "beach destination"
        elif "ski destination" in user_lower or "skiing" in user_lower:
            destination = "ski destination"
        elif "mountain" in user_lower and "destination" in user_lower:
            destination = "mountain destination"
        # Then check for specific destinations
        elif "thailand" in user_lower or "bangkok" in user_lower:
            destination = "Bangkok, Thailand"
        elif "bangalore" in user_lower or "bengaluru" in user_lower:
            destination = "Bangalore, India"
        elif "mumbai" in user_lower or "bombay" in user_lower:
            destination = "Mumbai, India"
        elif "delhi" in user_lower or "new delhi" in user_lower:
            destination = "Delhi, India"
        elif "hyderabad" in user_lower:
            destination = "Hyderabad, India"
        elif "chennai" in user_lower or "madras" in user_lower:
            destination = "Chennai, India"
        elif "kolkata" in user_lower or "calcutta" in user_lower:
            destination = "Kolkata, India"
        elif "zermatt" in user_lower:
            destination = "Zermatt, Switzerland"
        elif "japan" in user_lower:
            destination = "Japan"
        elif "new york" in user_lower:
            destination = "New York"
        elif "paris" in user_lower:
            destination = "Paris"
        elif "london" in user_lower:
            destination = "London"
        elif "tokyo" in user_lower:
            destination = "Tokyo"
        else:
            # Generic extraction for any location mentioned
            # Try to extract destination from patterns like "plan trip to X", "visit X", "travel to X"
            import re
            location_patterns = [
                r'(?:plan\s+(?:a\s+)?trip\s+to|visit|travel\s+to|going\s+to)\s+([A-Za-z][A-Za-z\s,\-]{1,30}?)(?:\s+next|\s+in|\s+for|\s*$|\.)',
                r'trip\s+to\s+([A-Za-z][A-Za-z\s,\-]{1,30}?)(?:\s+next|\s+in|\s+for|\s*$|\.)',
                r'to\s+([A-Za-z][A-Za-z\s,\-]{2,30}?)(?:\s+next|\s+in|\s+for|\s*$|\.)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, user_lower, re.IGNORECASE)
                if match:
                    potential_dest = match.group(1).strip()
                    # Clean up common trailing words
                    potential_dest = re.sub(r'\s+(next|in|for|on|at|this|month|year|week)$', '', potential_dest, flags=re.IGNORECASE)
                    if len(potential_dest.strip()) > 2:  # Must be more than 2 characters
                        destination = potential_dest.strip().title()
                        break
        
        # Extract duration if mentioned (only override if new one found)
        import re
        duration_patterns = [
            r'(\d+)[\s-]*days?',  # "7 days" or "7-day"  
            r'(\d+)[\s-]*nights?',  # "7 nights" or "7-night"
        ]
        for pattern in duration_patterns:
            duration_match = re.search(pattern, user_lower)
            if duration_match:
                duration = int(duration_match.group(1))
                break
        
        # Extract travel class (only override if new one found)
        if any(cls in user_lower for cls in ["business", "first class", "premium", "economy"]):
            if "business" in user_lower:
                travel_class = "business"
            elif "first" in user_lower:
                travel_class = "first"
            elif "premium" in user_lower:
                travel_class = "premium_economy"
            elif "economy" in user_lower:
                travel_class = "economy"
        
        # Extract budget (enhanced patterns) - only override if new one found
        budget_patterns = [
            r'(\d+(?:,\d+)?)\s*\$',  # "1000$"
            r'\$(\d+(?:,\d+)?)',  # "$1000"
            r'budget\s+(?:of\s+|is\s+)?\$?(\d+(?:,\d+)?)',  # "budget of 1000" or "budget is $1000"
            r'(\d+(?:,\d+)?)\s*(?:dollars?|usd)',  # "1000 dollars"
        ]
        for pattern in budget_patterns:
            budget_match = re.search(pattern, user_lower)
            if budget_match:
                budget = float(budget_match.group(1).replace(',', ''))
                break
        
        # Extract passenger count (only override if new one found)
        passenger_patterns = [
            r'(\d+)\s+people',  # "2 people"
            r'(\d+)\s+passengers?',  # "3 passengers"  
            r'(\d+)\s+travelers?',  # "4 travelers"
            r'for\s+(\d+)',  # "for 2"
        ]
        for pattern in passenger_patterns:
            passenger_match = re.search(pattern, user_lower)
            if passenger_match:
                passengers = int(passenger_match.group(1))
                break
        
        # Extract dates (enhanced patterns) - only override if new one found
        from datetime import datetime
        current_year = datetime.now().year
        
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            # Patterns without year - default to current year
            r'(?:jan|january)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Jan 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|january)(?!\s*,?\s*\d{4})',  # "15th January" (no year)
            r'(?:feb|february)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Feb 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:feb|february)(?!\s*,?\s*\d{4})',  # "15th February" (no year)
            r'(?:mar|march)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Mar 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:mar|march)(?!\s*,?\s*\d{4})',  # "15th March" (no year)
            r'(?:apr|april)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Apr 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:apr|april)(?!\s*,?\s*\d{4})',  # "15th April" (no year)
            r'(?:may)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "May 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:may)(?!\s*,?\s*\d{4})',  # "15th May" (no year)
            r'(?:jun|june)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Jun 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jun|june)(?!\s*,?\s*\d{4})',  # "15th June" (no year)
            r'(?:jul|july)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Jul 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jul|july)(?!\s*,?\s*\d{4})',  # "15th July" (no year)
            r'(?:aug|august)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Aug 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:aug|august)(?!\s*,?\s*\d{4})',  # "15th August" (no year)
            r'(?:sep|september)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Sep 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:sep|september)(?!\s*,?\s*\d{4})',  # "15th September" (no year)
            r'(?:oct|october)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Oct 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:oct|october)(?!\s*,?\s*\d{4})',  # "15th October" (no year)
            r'(?:nov|november)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Nov 25th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:nov|november)(?!\s*,?\s*\d{4})',  # "25th November" (no year)
            r'(?:dec|december)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Dec 15th" (no year)
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:dec|december)(?!\s*,?\s*\d{4})',  # "15th December" (no year)
            # Patterns with year
            r'(?:jan|january)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Jan 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|january)\s*,?\s*(\d{4})',  # "15th January 2025"
            r'(?:feb|february)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Feb 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:feb|february)\s*,?\s*(\d{4})',  # "15th February 2025"
            r'(?:mar|march)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Mar 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:mar|march)\s*,?\s*(\d{4})',  # "15th March 2025"
            r'(?:apr|april)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Apr 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:apr|april)\s*,?\s*(\d{4})',  # "15th April 2025"
            r'(?:may)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "May 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:may)\s*,?\s*(\d{4})',  # "15th May 2025"
            r'(?:jun|june)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Jun 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jun|june)\s*,?\s*(\d{4})',  # "15th June 2025"
            r'(?:jul|july)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Jul 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jul|july)\s*,?\s*(\d{4})',  # "15th July 2025"
            r'(?:aug|august)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Aug 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:aug|august)\s*,?\s*(\d{4})',  # "15th August 2025"
            r'(?:sep|september)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Sep 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:sep|september)\s*,?\s*(\d{4})',  # "15th September 2025"
            r'(?:oct|october)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Oct 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:oct|october)\s*,?\s*(\d{4})',  # "15th October 2025"
            r'(?:nov|november)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Nov 25th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:nov|november)\s*,?\s*(\d{4})',  # "25th November 2025"
            r'(?:dec|december)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Dec 15th 2025"
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:dec|december)\s*,?\s*(\d{4})',  # "15th December 2025"
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, user_lower)
            if date_match:
                if len(date_match.groups()) == 2:  # Month day year format
                    day = date_match.group(1)
                    year = date_match.group(2)
                elif len(date_match.groups()) == 1:  # Month day format (no year)
                    day = date_match.group(1)
                    year = str(current_year)
                else:
                    departure_date = date_match.group(1)
                    break
                
                # Determine month based on pattern matched
                if 'jan' in pattern:
                    departure_date = f"{year}-01-{day.zfill(2)}"
                elif 'feb' in pattern:
                    departure_date = f"{year}-02-{day.zfill(2)}"
                elif 'mar' in pattern:
                    departure_date = f"{year}-03-{day.zfill(2)}"
                elif 'apr' in pattern:
                    departure_date = f"{year}-04-{day.zfill(2)}"
                elif 'may' in pattern:
                    departure_date = f"{year}-05-{day.zfill(2)}"
                elif 'jun' in pattern:
                    departure_date = f"{year}-06-{day.zfill(2)}"
                elif 'jul' in pattern:
                    departure_date = f"{year}-07-{day.zfill(2)}"
                elif 'aug' in pattern:
                    departure_date = f"{year}-08-{day.zfill(2)}"
                elif 'sep' in pattern:
                    departure_date = f"{year}-09-{day.zfill(2)}"
                elif 'oct' in pattern:
                    departure_date = f"{year}-10-{day.zfill(2)}"
                elif 'nov' in pattern:
                    departure_date = f"{year}-11-{day.zfill(2)}"
                elif 'dec' in pattern:
                    departure_date = f"{year}-12-{day.zfill(2)}"
                else:
                    departure_date = f"{year}-09-{day.zfill(2)}"  # Default to September
                break
        
        # Apply intelligent defaults for comprehensive travel planning
        if not duration:
            if destination and any(intl in destination.lower() for intl in ["thailand", "japan", "europe", "paris", "london"]):
                duration = 7  # International destinations
            elif destination and "india" in destination.lower():
                duration = 4  # Indian city breaks
            else:
                duration = 5  # Other destinations
                
        if not budget:
            if destination and "thailand" in destination.lower():
                budget = 2500  # Thailand budget for comprehensive planning
            elif destination and "india" in destination.lower():
                budget = 1500  # Indian cities budget (more affordable)
            elif destination and any(expensive in destination.lower() for expensive in ["paris", "london", "switzerland", "zermatt"]):
                budget = 3500  # Expensive destinations
            else:
                budget = 3000  # Default international budget
                
        if not travel_class:
            travel_class = "business"  # Default for premium experience
            
        if passengers == 1:
            passengers = 2  # Default to 2 for better travel experience
            
        # Generate departure date if missing - handle year-only requests intelligently
        if not departure_date:
            from datetime import datetime, timedelta
            import re
            
            # Check if user mentioned a specific year in their request
            year_match = re.search(r'\b(20\d{2})\b', user_request)
            if year_match:
                mentioned_year = int(year_match.group(1))
                current_year = datetime.now().year
                current_date = datetime.now()
                
                if mentioned_year == current_year:
                    # Same year - suggest reasonable future date within the year
                    current_month = current_date.month
                    
                    if current_month <= 3:
                        # Q1 - suggest mid-year travel (6 months ahead)
                        target_date = current_date + timedelta(days=180)
                    elif current_month <= 6:
                        # Q2 - suggest later in year (4-5 months ahead)  
                        target_date = current_date + timedelta(days=120)
                    elif current_month <= 9:
                        # Q3 - suggest end of year travel (2-3 months ahead)
                        target_date = current_date + timedelta(days=90)
                    else:
                        # Q4 - suggest next year (3-4 months ahead)
                        target_date = current_date + timedelta(days=120)
                    
                    departure_date = target_date.strftime("%Y-%m-%d")
                elif mentioned_year > current_year:
                    # Future year - suggest reasonable date in that year
                    # Calculate similar time of year, with reasonable lead time
                    if current_date.month <= 6:
                        # First half of current year - suggest similar period in target year
                        target_month = max(3, current_date.month)  # At least March to avoid winter
                        target_day = min(current_date.day, 28)  # Ensure valid day for any month
                        departure_date = f"{mentioned_year}-{target_month:02d}-{target_day:02d}"
                    else:
                        # Second half of current year - suggest spring of target year
                        # Calculate a date 3-4 months into the target year
                        spring_months_in = 3 + (current_date.month % 4)  # 3-6 months into year
                        target_day = min(current_date.day, 28)  # Ensure valid day
                        target_date = datetime(mentioned_year, spring_months_in, target_day)
                        departure_date = target_date.strftime("%Y-%m-%d")
                else:
                    # Past year mentioned - default to 30 days from now
                    departure_date = (current_date + timedelta(days=30)).strftime("%Y-%m-%d")
            else:
                # No specific year mentioned - default to 30 days from now
                departure_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        fallback_requirements = TravelRequirements(
            destination=destination,
            event_name=event_name,
            event_type=event_type,
            duration=duration,
            departure_date=departure_date,
            budget=budget,
            travel_class=travel_class,
            passengers=passengers
        )
        
        # Dynamically determine missing critical fields (minimize with intelligent defaults)
        missing_fields = []
        requirements_dict = fallback_requirements.model_dump()
        
        # Only mark destination as missing if we couldn't extract any location info
        if not requirements_dict.get("destination"):
            missing_fields.append("destination")
        # Don't mark other fields as missing since we applied intelligent defaults
        
        fallback_result = {
            "requirements": requirements_dict,
            "missing_fields": missing_fields,
            "confidence_score": 0.8 if destination else 0.4,  # Higher confidence with destination + defaults
            "original_request": user_request,
            "mode": "fallback_extraction_with_intelligent_defaults",
            "suggested_defaults": {
                "duration_reasoning": f"Applied {duration}-day default for international travel to {destination}",
                "budget_reasoning": f"Estimated ${budget} for {passengers} people for {duration} days to {destination}",
                "passenger_assumption": f"Defaulted to {passengers} people for optimal travel experience",
                "recommended_travel_class": f"{travel_class} class for budget-conscious planning"
            },
            "planning_context": {
                "requires_comprehensive_planning": True,
                "defaults_applied": True,
                "destination_specificity": "extracted" if destination else "missing"
            }
        }
        
        return self.format_output(fallback_result)