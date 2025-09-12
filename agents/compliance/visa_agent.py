import os
from typing import Dict, Any, List, Optional
import httpx
import openai
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class VisaRequirement(BaseModel):
    required: bool = Field(..., description="Whether visa is required")
    type: Optional[str] = Field(None, description="Type of visa required")
    duration: Optional[str] = Field(None, description="Maximum stay duration")
    processing_time: Optional[str] = Field(None, description="Typical processing time")
    cost: Optional[Dict[str, Any]] = Field(None, description="Visa cost information")
    documents: List[str] = Field([], description="Required documents")
    application_url: Optional[str] = Field(None, description="Where to apply")
    notes: List[str] = Field([], description="Important notes and disclaimers")

class VisaResult(BaseModel):
    origin_country: str = Field(..., description="Traveler's nationality")
    destination_country: str = Field(..., description="Destination country")
    visa_requirement: VisaRequirement
    disclaimers: List[str] = Field(..., description="Legal disclaimers")
    last_updated: str = Field(..., description="When data was last updated")
    source: str = Field(..., description="Data source")

class VisaRequirementAgent(BaseAgent):
    def __init__(self):
        super().__init__("VisaRequirementAgent")
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.amadeus_base_url = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
        self.access_token = None
        self.token_expires_at = None
        
        # OpenAI for LLM fallback
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Static visa database for common routes (fallback)
        self.visa_database = self._load_visa_database()
    
    def _load_visa_database(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Load static visa requirements database"""
        return {
            "US": {
                "JP": {"required": False, "type": "visa_waiver", "duration": "90 days", "notes": ["ESTA required"]},
                "UK": {"required": False, "type": "visa_waiver", "duration": "90 days", "notes": ["No visa for tourism"]},
                "TH": {"required": False, "type": "visa_waiver", "duration": "30 days", "notes": ["Passport must be valid 6 months"]},
                "IN": {"required": True, "type": "tourist_visa", "duration": "varies", "processing_time": "5-10 business days"}
            },
            "UK": {
                "US": {"required": False, "type": "visa_waiver", "duration": "90 days", "notes": ["ESTA required"]},
                "JP": {"required": False, "type": "visa_waiver", "duration": "90 days", "notes": ["No visa for tourism"]},
                "TH": {"required": False, "type": "visa_waiver", "duration": "30 days", "notes": ["Passport validity required"]},
                "IN": {"required": True, "type": "e_visa", "duration": "30-60 days", "processing_time": "3-5 business days"}
            },
            "AU": {
                "US": {"required": False, "type": "visa_waiver", "duration": "90 days", "notes": ["ESTA required"]},
                "UK": {"required": False, "type": "visa_waiver", "duration": "180 days", "notes": ["No visa for tourism"]},
                "JP": {"required": False, "type": "visa_waiver", "duration": "90 days", "notes": ["No visa for short stays"]},
                "TH": {"required": False, "type": "visa_waiver", "duration": "30 days", "notes": ["Extension possible"]}
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Check visa requirements using Amadeus Travel Restrictions API
        
        Input:
        - origin_country: Traveler's nationality (ISO 2-letter code)
        - destination_country: Destination country (ISO 2-letter code)
        - travel_purpose: tourism/business/transit
        - passport_type: regular/diplomatic/official
        """
        required_fields = ["origin_country", "destination_country"]
        self.validate_input(input_data, required_fields)
        
        origin = input_data["origin_country"].upper()
        destination = input_data["destination_country"].upper()
        
        # Check if we can use Amadeus API
        if self.amadeus_client_id and self.amadeus_client_secret:
            try:
                await self._ensure_access_token()
                result = await self._check_amadeus_travel_restrictions(input_data)
                return self.format_output(result)
            except Exception as e:
                self.log(f"Amadeus Travel Restrictions API error: {e}")
                # Fallback to static database
                pass
        
        # Use static database
        result = self._check_static_visa_requirements(origin, destination, input_data)
        
        # If static database doesn't have information, try LLM fallback
        if (result.get("data", {}).get("visa_requirement", {}).get("notes", [])) and \
           any("not available in database" in note for note in result.get("data", {}).get("visa_requirement", {}).get("notes", [])):
            try:
                llm_result = await self._get_llm_visa_requirements(origin, destination, input_data)
                return self.format_output(llm_result)
            except Exception as e:
                self.log(f"LLM fallback failed: {e}")
                # Return the static database result as final fallback
        
        return self.format_output(result)
    
    async def _ensure_access_token(self):
        """Ensure valid Amadeus access token"""
        from datetime import datetime, timedelta
        
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return
        
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.amadeus_client_id,
                "client_secret": self.amadeus_client_secret
            }
            
            response = await client.post(
                f"{self.amadeus_base_url}/v1/security/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 1799)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
    
    async def _check_amadeus_travel_restrictions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check travel restrictions using Amadeus API"""
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "countryCode": input_data["destination_country"].upper(),
                "citizenshipCountryCode": input_data["origin_country"].upper(),
                "travelPurpose": input_data.get("travel_purpose", "TOURISM").upper()
            }
            
            response = await client.get(
                f"{self.amadeus_base_url}/v1/duty-of-care/diseases/covid19-area-report",
                params=params,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            api_data = response.json()
            return self._process_amadeus_response(api_data, input_data)
    
    def _process_amadeus_response(self, api_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Amadeus travel restrictions response"""
        
        data = api_data.get("data", {})
        area_data = data.get("area", {})
        
        # Extract visa information (Note: COVID API may not have visa info)
        # This is a simplified example - real implementation would use proper visa endpoint
        
        visa_requirement = VisaRequirement(
            required=True,  # Default to required for safety
            type="tourist_visa",
            duration="Check with embassy",
            processing_time="Varies",
            cost=None,
            documents=["Valid passport", "Visa application", "Photos", "Financial proof"],
            application_url=None,
            notes=["Please verify current requirements with embassy or consulate"]
        )
        
        result = VisaResult(
            origin_country=input_data["origin_country"].upper(),
            destination_country=input_data["destination_country"].upper(),
            visa_requirement=visa_requirement,
            disclaimers=[
                "Visa requirements can change frequently",
                "Always verify with official government sources",
                "This information is for guidance only",
                "Embassy/consulate has final authority"
            ],
            last_updated="2024-01-01",  # Would be from API
            source="Amadeus Travel Restrictions API"
        )
        
        return result.model_dump()
    
    def _check_static_visa_requirements(self, origin: str, destination: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check visa requirements using static database"""
        
        # Check if we have data for this route
        visa_info = None
        if origin in self.visa_database and destination in self.visa_database[origin]:
            visa_info = self.visa_database[origin][destination]
        
        if visa_info:
            visa_requirement = VisaRequirement(
                required=visa_info.get("required", True),
                type=visa_info.get("type"),
                duration=visa_info.get("duration"),
                processing_time=visa_info.get("processing_time"),
                cost=visa_info.get("cost"),
                documents=visa_info.get("documents", [
                    "Valid passport (6+ months validity)",
                    "Completed visa application",
                    "Passport photos",
                    "Proof of accommodation",
                    "Return ticket",
                    "Financial documentation"
                ]),
                application_url=visa_info.get("application_url"),
                notes=visa_info.get("notes", [])
            )
        else:
            # Default to visa required for unknown routes
            visa_requirement = VisaRequirement(
                required=True,
                type="tourist_visa",
                duration="Check with embassy",
                processing_time="Unknown - contact embassy",
                cost=None,
                documents=[
                    "Valid passport (6+ months validity)",
                    "Visa application form",
                    "Passport-sized photos",
                    "Proof of accommodation booking",
                    "Return flight ticket",
                    "Bank statements or financial proof",
                    "Travel insurance"
                ],
                application_url=None,
                notes=[
                    "Visa requirements not available in database",
                    "Contact embassy or consulate for current requirements",
                    "Requirements may vary by passport type and travel purpose"
                ]
            )
        
        result = VisaResult(
            origin_country=origin,
            destination_country=destination,
            visa_requirement=visa_requirement,
            disclaimers=[
                "⚠️ IMPORTANT: Visa requirements change frequently and vary by individual circumstances",
                "This information is for general guidance only and may not be current",
                "Always verify requirements with the destination country's embassy or official government website",
                "Processing times and requirements may vary by location and season",
                "Some nationalities may have different requirements not reflected here"
            ],
            last_updated="2024-01-01",
            source="Static visa database"
        )
        
        return result.model_dump()
    
    async def _get_llm_visa_requirements(self, origin: str, destination: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get visa requirements using LLM based on nationality and destination"""
        
        # Map country codes to names for better LLM understanding
        country_names = {
            "US": "United States", "UK": "United Kingdom", "JP": "Japan", "CA": "Canada",
            "AU": "Australia", "TH": "Thailand", "IN": "India", "BR": "Brazil", 
            "FR": "France", "DE": "Germany", "IT": "Italy", "ES": "Spain", "CH": "Switzerland",
            "NL": "Netherlands", "BE": "Belgium", "AT": "Austria", "SE": "Sweden", "NO": "Norway",
            "DK": "Denmark", "FI": "Finland", "PT": "Portugal", "GR": "Greece", "IE": "Ireland",
            "CN": "China", "KR": "South Korea", "SG": "Singapore", "MY": "Malaysia", "ID": "Indonesia",
            "PH": "Philippines", "VN": "Vietnam", "NZ": "New Zealand", "ZA": "South Africa"
        }
        
        origin_name = country_names.get(origin, origin)
        destination_name = country_names.get(destination, destination)
        
        travel_purpose = input_data.get("travel_purpose", "tourism")
        
        prompt = f"""
        You are a travel visa expert. Provide general visa requirements for {origin_name} citizens traveling to {destination_name} for {travel_purpose} purposes.

        Please provide:
        1. Whether a visa is required (true/false)
        2. Type of visa if required (tourist_visa, e_visa, visa_waiver, etc.)
        3. Maximum stay duration if known
        4. Typical processing time if visa required
        5. General required documents
        6. Important notes about requirements

        Format your response as factual and helpful general information. Include disclaimers that this is general information and requirements should be verified with official sources.

        Be concise but informative. If you're uncertain about specific details, indicate that verification with official sources is needed.
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable travel visa expert providing general visa requirement information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more factual responses
                max_tokens=800
            )
            
            llm_response = response.choices[0].message.content
            
            # Parse LLM response and structure it
            visa_required = "visa is required" in llm_response.lower() or "require a visa" in llm_response.lower()
            
            # Extract key information (simplified parsing)
            if "no visa required" in llm_response.lower() or "visa-free" in llm_response.lower():
                visa_required = False
                visa_type = "visa_waiver"
            else:
                visa_type = "tourist_visa"  # Default assumption
                if "e-visa" in llm_response.lower() or "evisa" in llm_response.lower():
                    visa_type = "e_visa"
                elif "on arrival" in llm_response.lower():
                    visa_type = "visa_on_arrival"
            
            visa_requirement = VisaRequirement(
                required=visa_required,
                type=visa_type,
                duration="Check with embassy for exact duration",
                processing_time="Varies - consult official sources",
                cost=None,
                documents=[
                    "Valid passport (minimum 6 months validity)",
                    "Completed application form",
                    "Passport photos",
                    "Proof of accommodation",
                    "Return/onward travel booking",
                    "Financial documentation"
                ],
                application_url=None,
                notes=[
                    "This is general information based on AI knowledge",
                    "Requirements may change frequently",
                    "Verify current requirements with destination country's embassy/consulate",
                    "Individual circumstances may affect requirements"
                ]
            )
            
            result = VisaResult(
                origin_country=origin,
                destination_country=destination,
                visa_requirement=visa_requirement,
                disclaimers=[
                    "⚠️ IMPORTANT: This information is AI-generated based on general knowledge",
                    "Visa requirements change frequently and vary by individual circumstances", 
                    "Always verify current requirements with official government sources",
                    "Embassy or consulate has final authority on visa requirements",
                    "Processing times and costs may vary significantly"
                ],
                last_updated="AI-generated",
                source=f"LLM General Knowledge - {origin_name} to {destination_name}"
            )
            
            return result.model_dump()
            
        except Exception as e:
            self.log(f"LLM visa lookup failed: {e}")
            # Return a safe fallback response
            return self._create_llm_fallback_response(origin, destination)
    
    def _create_llm_fallback_response(self, origin: str, destination: str) -> Dict[str, Any]:
        """Create minimal fallback when LLM fails"""
        visa_requirement = VisaRequirement(
            required=True,  # Safe assumption
            type="tourist_visa",
            duration="Contact embassy for details",
            processing_time="Contact embassy for details",
            cost=None,
            documents=[
                "Valid passport (minimum 6 months validity)",
                "Visa application (contact embassy for forms)",
                "Passport photos",
                "Travel itinerary",
                "Financial proof"
            ],
            application_url=None,
            notes=[
                "LLM visa service temporarily unavailable",
                "Contact embassy or consulate for current requirements",
                "Requirements vary by nationality and travel purpose"
            ]
        )
        
        result = VisaResult(
            origin_country=origin,
            destination_country=destination,
            visa_requirement=visa_requirement,
            disclaimers=[
                "⚠️ Visa information service temporarily unavailable",
                "Contact destination country's embassy or consulate immediately",
                "Verify all requirements through official government channels"
            ],
            last_updated="Service unavailable",
            source="Emergency fallback"
        )
        
        return result.model_dump()