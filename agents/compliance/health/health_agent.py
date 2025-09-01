"""
Health Agent for HOT Intelligent Travel Assistant

Specialized agent for handling travel health requirements, vaccinations, and medical advisories.
Adapted from the original HOT Travel Assistant project and refined for MySQL backend.
"""

import os
from typing import Dict, List, Optional, Any
import structlog
from agents.base_agent import BaseAgent
from models.agent_models import AgentResponse

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    vertexai = None
    GenerativeModel = None
    VERTEX_AI_AVAILABLE = False

logger = structlog.get_logger()
 
 
class HealthAgent(BaseAgent):
    """
    Health requirements and documentation agent.
   
    Handles all health-related queries including requirements, processing times,
    costs, and application procedures for various destinations.
    """
    
    def __init__(self):
        super().__init__("HealthAgent")
        self.model = self._initialize_ai_model()
        self.health_data = self._load_health_database()
   
    def _initialize_ai_model(self):
        """Initialize Vertex AI model if available and authorized"""
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
           
            if project_id and VERTEX_AI_AVAILABLE:
                vertexai.init(project=project_id, location=location)
                model = GenerativeModel(model_name)
                logger.info(f"✅ Health Agent: Vertex AI initialized: {project_id} - {model_name}")
                return model
            else:
                logger.info("ℹ️ Health Agent: Using fallback mode (no AI)")
                return None
        except Exception as e:
            logger.error(f"❌ Health Agent: Failed to initialize Vertex AI: {e}")
            return None
   
    def _load_health_database(self) -> Dict:
        """Load hardcoded health data for fallback mode"""
        return {
            "brazil": {
                "vaccinations_recommended": ["Yellow Fever", "Typhoid", "Hepatitis A"],
                "malaria_risk": "Present in Amazonian regions. Prophylaxis recommended.",
                "advisories": ["Zika virus is a risk. Pregnant women should consult a doctor.", "Dengue fever is common."],
                "emergency_number": "192 (Ambulance)"
            },
            "kenya": {
                "vaccinations_required": ["Yellow Fever (proof of vaccination required for entry)"],
                "vaccinations_recommended": ["Typhoid", "Hepatitis A", "Tetanus", "Polio"],
                "malaria_risk": "High risk in most of the country. Prophylaxis is essential.",
                "advisories": ["Cholera outbreaks can occur.", "Drink bottled or boiled water."],
                "emergency_number": "999"
            },
            "thailand": {
                "vaccinations_recommended": ["Hepatitis A", "Typhoid"],
                "malaria_risk": "Low risk in most tourist areas, higher in rural and border regions.",
                "advisories": ["Dengue fever is prevalent, especially during rainy season.", "Be cautious with street food to avoid food poisoning."],
                "emergency_number": "1669 (Medical Emergency)"
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute health requirements check - new project interface"""
        self.validate_input(input_data, ["destination"])
        
        destination = input_data["destination"].lower()
        
        # Try AI response first if available
        if self.model:
            try:
                response = await self._generate_ai_response_new(destination)
            except Exception as e:
                logger.error(f"Health Agent AI error: {e}")
                response = self._generate_fallback_response_new(destination)
        else:
            response = self._generate_fallback_response_new(destination)
        
        return self.format_output({
            "health_requirements": response,
            "destination": destination,
            "disclaimer": "Always consult a qualified medical professional for personalized travel health advice."
        })
   
    async def can_handle(self, query: str) -> bool:
        """Check if query is health-related"""
        query_lower = query.lower()
        health_keywords = [
            "health", "vaccine", "vaccination", "doctor", "hospital", "medical",
            "malaria", "zika", "dengue", "yellow fever", "typhoid", "cholera",
            "pharmacy", "prescription", "insurance", "clinic",
            "brazil", "kenya", "thailand"
        ]
        return any(keyword in query_lower for keyword in health_keywords)
   
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process health-related query"""
        logger.info(f"Health Agent processing: {query}")
       
        # Try AI response first if available
        if self.model:
            try:
                return await self._generate_ai_response(query)
            except Exception as e:
                logger.error(f"Health Agent AI error: {e}")
       
        # Fallback to hardcoded response
        return self._generate_fallback_response(query)
   
    async def _generate_ai_response(self, query: str) -> AgentResponse:
        """Generate AI-powered health response"""
        prompt = f"""You are a Travel Health Specialist for HOT Travel Assistant.
 
User Query: "{query}"
 
Please provide comprehensive travel health information for the destination mentioned, including:
1. Required and recommended vaccinations.
2. Information on prevalent diseases (like Malaria, Zika, Dengue).
3. General health advisories (food/water safety, etc.).
4. Important notes and warnings.
 
Format your response with clear sections using markdown-style headers and bullet points.
Keep it informative but concise. Always remind users to consult a medical professional.
 
If the query is not about travel health, politely redirect to health-related topics."""
 
        response = await self.model.generate_content_async(prompt)
       
        suggestions = [
            "What vaccines do I need for Brazil?",
            "Is there a malaria risk in Kenya?",
            "Health tips for traveling in Thailand"
        ]
       
        return AgentResponse(
            response=response.text,
            suggestions=suggestions,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={"mode": "ai", "model": "vertex_ai"}
        )
   
    def _generate_fallback_response(self, query: str) -> AgentResponse:
        """Generate fallback response using hardcoded data"""
        analysis = self._analyze_query(query)
        destination = analysis["destination"]
       
        if not destination:
            return AgentResponse(
                response=self._get_general_health_info(),
                suggestions=[
                    "What are the health risks in Brazil?",
                    "Do I need vaccinations for Kenya?",
                    "Is Thailand safe for travel?"
                ],
                agent_type=self.agent_type,
                confidence=0.7,
                metadata={"mode": "fallback", "detected_destination": None}
            )
       
        response_text = self._get_destination_response(destination)
        suggestions = [
            f"What vaccinations are needed for {destination.title()}?",
            f"Tell me about malaria risk in {destination.title()}.",
            "Ask about another country"
        ]
       
        return AgentResponse(
            response=response_text,
            suggestions=suggestions,
            agent_type=self.agent_type,
            confidence=0.8,
            metadata={"mode": "fallback", "detected_destination": destination}
        )
   
    def _analyze_query(self, query: str) -> Dict:
        """Analyze query to extract destination and intent"""
        query_lower = query.lower()
       
        # Extract destination
        destination = None
        if "brazil" in query_lower:
            destination = "brazil"
        elif "kenya" in query_lower:
            destination = "kenya"
        elif "thailand" in query_lower:
            destination = "thailand"
       
        # Extract intent
        intent = "general"
        if any(word in query_lower for word in ["vaccine", "vaccination", "shot"]):
            intent = "vaccinations"
        elif any(word in query_lower for word in ["malaria", "zika", "dengue", "disease"]):
            intent = "diseases"
        elif any(word in query_lower for word in ["safe", "advice", "tip"]):
            intent = "advisories"
       
        return {"destination": destination, "intent": intent}
   
    def _get_general_health_info(self) -> str:
        """Get general travel health information"""
        return """⚕️ **HOT Travel Assistant - Health Specialist**
 
I specialize in travel health requirements and advisories!
 
**Popular Health Topics:**
• 🇧🇷 **Brazil** - Ask "What vaccines for Brazil?"
• 🇰🇪 **Kenya** - Ask "Is there malaria risk in Kenya?"
• 🇹🇭 **Thailand** - Ask "Health tips for Thailand"
 
**What I can help with:**
• Required and recommended vaccinations
• Information on diseases like Malaria, Zika, and Dengue
• Food and water safety tips
• General health advisories
 
⚠️ **Disclaimer**: I am an AI assistant. Always consult a qualified medical professional before traveling."""
   
    def _get_destination_response(self, destination: str) -> str:
        """Get destination-specific health response"""
        data = self.health_data.get(destination, {})
       
        if not data:
            return "Sorry, I don't have health information for that destination yet."
 
        response_parts = []
        if destination == "brazil":
            response_parts.append("🇧🇷 **Brazil Health Information**\n")
        elif destination == "kenya":
            response_parts.append("🇰🇪 **Kenya Health Information**\n")
        elif destination == "thailand":
            response_parts.append("🇹🇭 **Thailand Health Information**\n")
 
        if data.get("vaccinations_required"):
            response_parts.append("**Required Vaccinations:**")
            response_parts.append('\n'.join(f"• {req}" for req in data["vaccinations_required"]))
       
        if data.get("vaccinations_recommended"):
            response_parts.append("\n**Recommended Vaccinations:**")
            response_parts.append('\n'.join(f"• {req}" for req in data["vaccinations_recommended"]))
 
        if data.get("malaria_risk"):
            response_parts.append(f"\n**Malaria Risk:**\n• {data['malaria_risk']}")
 
        if data.get("advisories"):
            response_parts.append("\n**Health Advisories:**")
            response_parts.append('\n'.join(f"• {adv}" for adv in data["advisories"]))
 
        response_parts.append(f"\n**Emergency Number:** {data.get('emergency_number', 'N/A')}")
        response_parts.append("\n\n⚠️ **Disclaimer**: Please consult a travel doctor for personalized medical advice.")
 
        return "\n".join(response_parts)
   
    def get_capabilities(self) -> List[str]:
        """Return health agent capabilities"""
        return [
            "Vaccination requirements and recommendations",
            "Malaria and other disease risk assessments",
            "General travel health advisories",
            "Food and water safety tips",
            "Finding local medical services"
        ]
    
    async def _generate_ai_response_new(self, destination: str) -> Dict:
        """Generate AI-powered health response for new project"""
        prompt = f"""You are a Travel Health Specialist for HOT Travel Assistant.

Destination: {destination}

Please provide comprehensive travel health information for {destination}, including:
1. Required and recommended vaccinations
2. Information on prevalent diseases (like Malaria, Zika, Dengue)
3. General health advisories (food/water safety, etc.)
4. Important notes and warnings

Format your response as structured data that can be easily processed.
Always remind users to consult a medical professional."""

        response = await self.model.generate_content_async(prompt)
        
        return {
            "ai_response": response.text,
            "mode": "ai_powered"
        }
    
    def _generate_fallback_response_new(self, destination: str) -> Dict:
        """Generate fallback response using hardcoded data for new project"""
        health_info = self.health_data.get(destination, {})
        
        if not health_info:
            return {
                "message": f"Health information not available for {destination}",
                "recommendation": "Please consult a travel health clinic or doctor",
                "mode": "no_data"
            }
        
        return {
            "vaccinations_required": health_info.get("vaccinations_required", []),
            "vaccinations_recommended": health_info.get("vaccinations_recommended", []),
            "malaria_risk": health_info.get("malaria_risk", "Unknown"),
            "advisories": health_info.get("advisories", []),
            "emergency_number": health_info.get("emergency_number", "Unknown"),
            "mode": "database_lookup"
        }