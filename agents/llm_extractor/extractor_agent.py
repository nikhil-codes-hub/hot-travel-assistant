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
        
        # Check if AI is available
        if not self.ai_available:
            return self._generate_fallback_extraction(user_request)
        
        try:
            # Create extraction prompt
            prompt = self._create_extraction_prompt(user_request)
            
            # Call AI API
            if self.ai_provider == "vertex":
                response = await self._call_vertex_ai(prompt)
            else:
                response = self.model.generate_content(prompt)
            
            # Parse response
            if self.ai_provider == "vertex":
                extracted_data = self._parse_response(response, user_request)
            else:
                extracted_data = self._parse_response(response.text, user_request)
            
            return self.format_output(extracted_data)
        except Exception:
            return self._generate_fallback_extraction(user_request)
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-1.5-pro')
        response = await model.generate_content_async(prompt)
        return response.text
    
    def _create_extraction_prompt(self, user_request: str) -> str:
        return f"""
You are a travel requirements extraction specialist. Extract travel requirements from the user request with NO GUESSING OR HALLUCINATION.

CRITICAL RULES:
1. Only extract explicitly mentioned information
2. If information is vague or missing, mark as null and add to missing_fields
3. Be conservative - err on the side of asking for clarification
4. Do not make assumptions about dates, budgets, or preferences

User Request: "{user_request}"

Extract the following information and return ONLY valid JSON:
{{
    "requirements": {{
        "destination": "exact destination name if clearly specified, null if vague like 'somewhere warm' or 'Europe'",
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
- Include destination if vague or missing
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
            # Fallback parsing
            return {
                "requirements": TravelRequirements().model_dump(),
                "missing_fields": ["destination", "dates", "budget", "passengers"],
                "confidence_score": 0.1,
                "original_request": original_request,
                "parsing_error": str(e)
            }
    
    def _generate_fallback_extraction(self, user_request: str) -> Dict[str, Any]:
        """Generate a basic extraction without AI"""
        # Simple keyword-based extraction as fallback
        destination = None
        duration = None
        
        if "japan" in user_request.lower():
            destination = "Japan"
        elif "new york" in user_request.lower():
            destination = "New York"
        
        # Extract duration if mentioned
        import re
        duration_match = re.search(r'(\d+)\s*days?', user_request.lower())
        if duration_match:
            duration = int(duration_match.group(1))
        
        fallback_requirements = TravelRequirements(
            destination=destination,
            duration=duration
        )
        
        fallback_result = {
            "requirements": fallback_requirements.model_dump(),
            "missing_fields": ["departure_date", "budget", "travel_class"],
            "confidence_score": 0.3,
            "original_request": user_request,
            "mode": "fallback_extraction"
        }
        
        return self.format_output(fallback_result)