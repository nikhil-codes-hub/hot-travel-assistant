import os
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent
from agents.cache.llm_cache import LLMCache

class TravelRequirements(BaseModel):
    destination: Optional[str] = Field(None, description="Specific destination if mentioned")
    destination_type: Optional[str] = Field(None, description="Type of destination (beach, mountains, city, etc.)")
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
        self.ai_provider = os.getenv("AI_PROVIDER", "gemini")
        self.ai_available = False
        
        # Initialize LLM response cache
        cache_dir = os.getenv("LLM_CACHE_DIR", "cache/llm_responses")
        cache_duration = int(os.getenv("LLM_CACHE_DURATION_HOURS", "24"))
        self.cache = LLMCache(cache_dir=cache_dir, cache_duration_hours=cache_duration)
        
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
            self.log("⚠️  LLM not available - applying intelligent defaults")
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
        
        model = GenerativeModel('gemini-1.5-pro')
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
- Enable full travel planning workflow including attractions, flights, hotels, visa requirements, health advisories
- Handle both specific destinations (Thailand, Paris) and vague requests (somewhere warm, tropical place)

CRITICAL RULES:
1. Extract all explicitly mentioned travel information
2. For destinations (specific OR vague): Always enable comprehensive planning
3. Apply INTELLIGENT DEFAULTS for missing parameters to enable comprehensive planning:
   - Duration: Suggest appropriate length based on destination (7 days international, 4-5 domestic)
   - Passengers: Default to 2 people for better travel experience
   - Budget: Suggest realistic range based on destination and duration
   - Travel Class: Default to economy for budget planning
4. MINIMIZE missing_fields - only mark as missing if absolutely critical and cannot be defaulted
5. Vague destinations like 'Thailand next month' should trigger full travel planning workflow
6. Never mark destination as missing if ANY location hint is provided
7. If conversation context exists, merge new information with existing context{context_info}

User Request: "{user_request}"

Extract the following information and return ONLY valid JSON with intelligent defaults:
{{
    "requirements": {{
        "destination": "Always extract if any location is mentioned - specific ('Thailand', 'Paris') or vague ('somewhere tropical', 'beach destination', 'Europe'). Only null if absolutely no location mentioned",
        "destination_type": "Infer from context: beach/mountains/city/adventure/cultural/romantic/tropical/ski/etc",
        "departure_date": "YYYY-MM-DD if specific date, approximate if relative ('next month' -> '2025-12-01'), or suggest reasonable near-future date",
        "return_date": "YYYY-MM-DD if return date specified, calculate based on duration if available",
        "duration": "Extract if mentioned, OR suggest intelligent default: 7 days for international, 4-5 days for domestic/city breaks, 10-14 days for Asia/distant destinations",
        "budget": "Extract if currency mentioned, OR suggest reasonable range based on destination (e.g., 1500-3000 for Thailand, 2000-4000 for Europe per person for 7 days)",
        "budget_currency": "currency code if specified, 'USD' as default",
        "passengers": "Extract if mentioned, default to 2 people for better travel experience and planning",
        "children": "number of children if explicitly mentioned, null otherwise",
        "travel_class": "economy/premium_economy/business/first if mentioned, 'economy' as default for budget planning",
        "accommodation_type": "hotel/resort/hostel/apartment/bnb if mentioned, suggest based on destination and inferred budget",
        "special_requirements": ["explicit requirements or inferred from destination/context"]
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
                travel_class="economy",  # Default to economy for budget planning
                budget_currency="USD"
            )
            requirements_dict = default_requirements.model_dump()
            
            # Try to extract basic destination from original request
            user_lower = original_request.lower()
            if "thailand" in user_lower:
                requirements_dict["destination"] = "Thailand"
                requirements_dict["budget"] = 2000  # Reasonable Thailand budget for 2 people
                requirements_dict["destination_type"] = "tropical"
            elif "paris" in user_lower:
                requirements_dict["destination"] = "Paris"
                requirements_dict["duration"] = 5  # City break duration
                requirements_dict["budget"] = 2500
            elif any(pattern in user_lower for pattern in ["beach", "tropical", "warm"]):
                requirements_dict["destination"] = "tropical beach destination"
                requirements_dict["destination_type"] = "beach"
                requirements_dict["budget"] = 2500
            
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
                    "recommended_travel_class": "Economy class for budget-conscious planning"
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
        elif "thailand" in user_lower:
            destination = "Thailand"
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
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
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
                    # Determine month based on pattern matched
                    if 'nov' in pattern:
                        departure_date = f"{year}-11-{day.zfill(2)}"
                    elif 'dec' in pattern:
                        departure_date = f"{year}-12-{day.zfill(2)}"
                    else:
                        departure_date = f"{year}-11-{day.zfill(2)}"  # Default to November
                else:
                    departure_date = date_match.group(1)
                break
        
        # Apply intelligent defaults for comprehensive travel planning
        if not duration:
            if destination and any(intl in destination.lower() for intl in ["thailand", "japan", "europe", "paris", "london"]):
                duration = 7  # International destinations
            else:
                duration = 5  # Domestic/city breaks
                
        if not budget:
            if destination and "thailand" in destination.lower():
                budget = 2500  # Thailand budget for comprehensive planning
            elif destination and any(expensive in destination.lower() for expensive in ["paris", "london", "switzerland", "zermatt"]):
                budget = 3500  # Expensive destinations
            else:
                budget = 2000  # Default international budget
                
        if not travel_class:
            travel_class = "economy"  # Default for budget planning
            
        if passengers == 1:
            passengers = 2  # Default to 2 for better travel experience
            
        # Generate departure date if missing (30 days from now for better planning)
        if not departure_date:
            from datetime import datetime, timedelta
            departure_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        fallback_requirements = TravelRequirements(
            destination=destination,
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