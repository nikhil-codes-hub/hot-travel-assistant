import os
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from google.cloud import aiplatform
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent

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
                    self.model = genai.GenerativeModel('gemini-1.5-pro')
                    self.ai_available = True
        except Exception:
            self.ai_available = False
            self.model = None
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        self.validate_input(input_data, ["user_request"])
        
        user_request = input_data["user_request"]
        conversation_context = input_data.get("conversation_context", {})
        
        # Check if AI is available
        if not self.ai_available:
            return self._generate_fallback_extraction(user_request, conversation_context)
        
        try:
            # Create extraction prompt with conversation context
            prompt = self._create_extraction_prompt(user_request, conversation_context)
            
            # Call AI API
            if self.ai_provider == "vertex":
                response = await self._call_vertex_ai(prompt)
            else:
                response = self.model.generate_content(prompt)
            
            # Parse response
            if self.ai_provider == "vertex":
                extracted_data = self._parse_response(response, user_request, conversation_context)
            else:
                extracted_data = self._parse_response(response.text, user_request, conversation_context)
            
            return self.format_output(extracted_data)
        except Exception:
            return self._generate_fallback_extraction(user_request, conversation_context)
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-1.5-pro')
        response = await model.generate_content_async(prompt)
        return response.text
    
    def _create_extraction_prompt(self, user_request: str, conversation_context: Dict[str, Any] = None) -> str:
        context_info = ""
        if conversation_context:
            context_info = f"""

PREVIOUS CONVERSATION CONTEXT:
{conversation_context}

IMPORTANT: If the user request provides new information that wasn't in the previous context, update those fields. If the user request doesn't mention a field that exists in the previous context, keep the previous value."""

        return f"""
You are a travel requirements extraction specialist. Extract travel requirements from the user request with NO GUESSING OR HALLUCINATION.

CRITICAL RULES:
1. Only extract explicitly mentioned information from the current user request
2. If information is vague or missing, mark as null and add to missing_fields
3. Be conservative - err on the side of asking for clarification
4. Do not make assumptions about dates, budgets, or preferences
5. If conversation context exists, merge new information with existing context{context_info}

User Request: "{user_request}"

Extract the following information and return ONLY valid JSON:
{{
    "requirements": {{
        "destination": "destination as mentioned - can be specific ('Paris') or vague ('somewhere snowy', 'beach destination'). Only null if not mentioned at all",
        "destination_type": "type if mentioned: beach/mountains/city/adventure/cultural/romantic etc",
        "departure_date": "YYYY-MM-DD if specific date given, null for 'next week'/'this summer'",
        "return_date": "YYYY-MM-DD if return date specified, null otherwise",
        "duration": "exact number of days/nights if mentioned, null otherwise",
        "budget": "numeric amount only if currency value given, null for 'cheap'/'expensive'",
        "budget_currency": "currency code if specified, null otherwise",
        "passengers": "total number including adults and children, 1 if not specified",
        "children": "number of children if explicitly mentioned, null otherwise",
        "travel_class": "economy/premium_economy/business/first if mentioned, null otherwise",
        "accommodation_type": "hotel/resort/hostel/apartment/bnb if mentioned, null otherwise",
        "special_requirements": ["explicit requirements: wheelchair_access, vegetarian_meals, pet_travel etc"]
    }},
    "missing_fields": ["list CRITICAL fields needing clarification for booking"],
    "confidence_score": "0.0-1.0 based on clarity and completeness of request"
}}

MISSING FIELDS PRIORITY:
- Always include departure_date if not specified
- Include budget if not specified
- Include travel_class if not specified
- Include destination ONLY if completely missing (not if vague like 'somewhere warm')
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
            
            return result.model_dump()
            
        except Exception as e:
            # Fallback parsing - determine missing fields dynamically
            default_requirements = TravelRequirements()
            requirements_dict = default_requirements.model_dump()
            
            # Determine missing critical fields
            missing_fields = []
            critical_fields = {
                "destination": "destination",
                "departure_date": "departure date", 
                "duration": "trip duration",
                "budget": "budget",
                "travel_class": "travel class"
            }
            
            for field, display_name in critical_fields.items():
                if not requirements_dict.get(field):
                    missing_fields.append(display_name)
            
            return {
                "requirements": requirements_dict,
                "missing_fields": missing_fields,
                "confidence_score": 0.1,
                "original_request": original_request,
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
        elif "beach destination" in user_lower or "beaches" in user_lower:
            destination = "beach destination"
        elif "ski destination" in user_lower or "skiing" in user_lower:
            destination = "ski destination"
        elif "mountain" in user_lower and "destination" in user_lower:
            destination = "mountain destination"
        # Then check for specific destinations
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
        
        fallback_requirements = TravelRequirements(
            destination=destination,
            duration=duration,
            departure_date=departure_date,
            budget=budget,
            travel_class=travel_class,
            passengers=passengers
        )
        
        # Dynamically determine missing critical fields
        missing_fields = []
        requirements_dict = fallback_requirements.model_dump()
        
        # Critical fields that should be flagged if missing
        critical_fields = {
            "destination": "destination",
            "departure_date": "departure date", 
            "duration": "trip duration",
            "budget": "budget",
            "travel_class": "travel class"
        }
        
        for field, display_name in critical_fields.items():
            if not requirements_dict.get(field):
                missing_fields.append(display_name)
        
        fallback_result = {
            "requirements": requirements_dict,
            "missing_fields": missing_fields,
            "confidence_score": 0.3,
            "original_request": user_request,
            "mode": "fallback_extraction"
        }
        
        return self.format_output(fallback_result)