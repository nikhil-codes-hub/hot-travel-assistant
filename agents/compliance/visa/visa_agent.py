"""
Visa Agent for HOT Intelligent Travel Assistant

Specialized agent for handling visa requirements, documentation, and travel authorization queries.
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


class VisaAgent(BaseAgent):
    """
    Visa requirements and documentation agent.
    
    Handles all visa-related queries including requirements, processing times,
    costs, and application procedures for various destinations.
    """
    
    def __init__(self):
        super().__init__("VisaAgent")
        self.model = self._initialize_ai_model()
        self.visa_data = self._load_visa_database()
    
    def _initialize_ai_model(self):
        """Initialize Vertex AI model if available and authorized"""
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            
            if project_id and VERTEX_AI_AVAILABLE:
                vertexai.init(project=project_id, location=location)
                model = GenerativeModel(model_name)
                logger.info(f"✅ Visa Agent: Vertex AI initialized: {project_id} - {model_name}")
                return model
            else:
                logger.info("ℹ️ Visa Agent: Using fallback mode (no AI)")
                return None
        except Exception as e:
            logger.error(f"❌ Visa Agent: Failed to initialize Vertex AI: {e}")
            return None
    
    def _load_visa_database(self) -> Dict:
        """Load hardcoded visa data for fallback mode"""
        return {
            "japan": {
                "visa_free": ["US", "UK", "Canada", "Australia", "Germany", "France", "Italy", "Spain", "Netherlands"],
                "visa_required": ["China", "India", "Russia", "Philippines", "Pakistan", "Bangladesh"],
                "duration": "90 days",
                "requirements": ["Valid passport (6+ months)", "Return ticket", "Proof of funds ($3000+)"],
                "processing_time": "5-7 business days",
                "cost": "¥3,000 ($20)"
            },
            "china": {
                "visa_required": "Most nationalities",
                "e_visa": ["US", "UK", "Canada", "Australia", "Germany", "France"],
                "duration": "30-90 days",
                "requirements": ["Passport (6+ months, 2 blank pages)", "Photo", "Flight booking", "Hotel booking", "Bank statements"],
                "processing_time": "3-5 days (e-visa), 4-10 days (regular)",
                "cost": "$25-60"
            },
            "india": {
                "e_visa": ["US", "UK", "Canada", "Australia", "Germany", "France", "Japan"],
                "duration": "30 days to 5 years",
                "requirements": ["Passport (6+ months, 2 blank pages)", "Photo", "Travel itinerary", "Accommodation proof"],
                "processing_time": "3-5 business days",
                "cost": "$10-80"
            },
            "schengen": {
                "visa_free": ["US", "UK", "Canada", "Australia", "Japan", "South Korea", "Singapore"],
                "visa_required": ["China", "India", "Russia", "Philippines", "Thailand"],
                "duration": "90 days in 180-day period",
                "requirements": ["Passport (3+ months validity)", "Travel insurance (€30,000)", "Accommodation proof", "Financial proof"],
                "processing_time": "15 calendar days",
                "cost": "€80"
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute visa requirements check - new project interface"""
        self.validate_input(input_data, ["destination", "nationality"])
        
        destination = input_data["destination"].lower()
        nationality = input_data["nationality"]
        
        # Try AI response first if available
        if self.model:
            try:
                response = await self._generate_ai_response_new(destination, nationality)
            except Exception as e:
                logger.error(f"Visa Agent AI error: {e}")
                response = self._generate_fallback_response_new(destination, nationality)
        else:
            response = self._generate_fallback_response_new(destination, nationality)
        
        return self.format_output({
            "visa_requirements": response,
            "destination": destination,
            "nationality": nationality,
            "disclaimer": "Always verify with official embassy sources for current requirements."
        })
    
    async def can_handle(self, query: str) -> bool:
        """Check if query is visa-related"""
        query_lower = query.lower()
        visa_keywords = [
            "visa", "passport", "entry", "documentation", 
            "travel permit", "authorization", "embassy", "consulate",
            "japan", "china", "india", "europe", "schengen"
        ]
        return any(keyword in query_lower for keyword in visa_keywords)
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process visa-related query"""
        logger.info(f"Visa Agent processing: {query}")
        
        # Try AI response first if available
        if self.model:
            try:
                return await self._generate_ai_response(query)
            except Exception as e:
                logger.error(f"Visa Agent AI error: {e}")
        
        # Fallback to hardcoded response
        return self._generate_fallback_response(query)
    
    async def _generate_ai_response(self, query: str) -> AgentResponse:
        """Generate AI-powered visa response"""
        prompt = f"""You are a Visa Requirements Specialist for HOT Travel Assistant.

User Query: "{query}"

Please provide comprehensive visa information including:
1. Whether a visa is required
2. Visa-free options if available  
3. Required documents
4. Processing times and costs
5. Important notes and warnings

Format your response with clear sections using markdown-style headers and bullet points.
Keep it informative but concise. Always remind users to verify with official sources.

If the query is not about visa requirements, politely redirect to visa-related topics."""

        response = await self.model.generate_content_async(prompt)
        
        suggestions = [
            "What documents do I need?",
            "How long does processing take?", 
            "What are the costs?",
            "Tell me about another country"
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
                response=self._get_general_visa_info(),
                suggestions=[
                    "Do I need a visa for Japan?",
                    "What are China visa requirements?",
                    "How to get India visa?", 
                    "Do I need Schengen visa?"
                ],
                agent_type=self.agent_type,
                confidence=0.7,
                metadata={"mode": "fallback", "detected_destination": None}
            )
        
        response_text = self._get_destination_response(destination)
        suggestions = [
            f"What documents do I need for {destination.title()} visa?",
            f"How long does {destination.title()} visa processing take?",
            f"What is the cost of {destination.title()} visa?",
            "Do I need a visa for another country?"
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
        if "japan" in query_lower or "japanese" in query_lower:
            destination = "japan"
        elif "china" in query_lower or "chinese" in query_lower:
            destination = "china"
        elif "india" in query_lower or "indian" in query_lower:
            destination = "india"
        elif any(country in query_lower for country in ["europe", "schengen", "germany", "france", "italy", "spain"]):
            destination = "schengen"
        
        # Extract intent
        intent = "general"
        if any(word in query_lower for word in ["need", "require", "necessary"]):
            intent = "requirements"
        elif any(word in query_lower for word in ["document", "paperwork"]):
            intent = "documents"
        elif any(word in query_lower for word in ["time", "long", "process"]):
            intent = "processing"
        elif any(word in query_lower for word in ["cost", "fee", "price"]):
            intent = "cost"
        
        return {"destination": destination, "intent": intent}
    
    def _get_general_visa_info(self) -> str:
        """Get general visa information"""
        return """🌍 **HOT Travel Assistant - Visa Specialist**

I specialize in visa requirements for international travel!

**Popular Destinations:**
• 🇯🇵 **Japan** - Ask "Do I need a visa for Japan?"
• 🇨🇳 **China** - Ask "What are China visa requirements?"
• 🇮🇳 **India** - Ask "How to get India visa?"
• 🇪🇺 **Europe** - Ask "Do I need Schengen visa?"

**What I can help with:**
• Visa requirements by destination
• Required documents
• Processing times and costs
• Application procedures

⚠️ **Note**: Always verify with official embassy sources for current requirements."""
    
    def _get_destination_response(self, destination: str) -> str:
        """Get destination-specific visa response"""
        data = self.visa_data.get(destination, {})
        
        if destination == "japan":
            return f"""🇯🇵 **Japan Visa Requirements**

**Visa-Free Countries ({data.get('duration', '90 days')}):**
• United States, Canada, UK, Australia
• Most EU countries (Germany, France, Italy, Spain)

**Visa Required:**
• China, India, Russia, Philippines, Pakistan

**Requirements for Visa-Free Entry:**
• {chr(10).join('• ' + req for req in data.get('requirements', []))}

**If Visa Required:**
• **Processing:** {data.get('processing_time', 'N/A')}
• **Cost:** {data.get('cost', 'N/A')}
• **Documents:** Passport, photos, application form, itinerary

⚠️ Always verify with Japanese consulate for current requirements."""
        
        elif destination == "china":
            return f"""🇨🇳 **China Visa Requirements**

**Visa Required** for most nationalities

**E-Visa Available:**
• Processing: {data.get('processing_time', 'N/A')}
• Duration: {data.get('duration', 'N/A')}
• Cost: {data.get('cost', 'N/A')}

**Required Documents:**
• {chr(10).join('• ' + req for req in data.get('requirements', []))}

**Special Cases:**
• Transit visa-free: 24-144 hours (selected cities)
• Hainan Province: 30-day visa-free for many countries

⚠️ Check Chinese embassy website for latest updates."""
        
        elif destination == "india":
            return f"""🇮🇳 **India Visa Requirements**

**E-Visa Available** for most countries

**E-Tourist Visa:**
• Processing: {data.get('processing_time', 'N/A')}
• Duration: {data.get('duration', 'N/A')}
• Cost: {data.get('cost', 'N/A')}

**Required Documents:**
• {chr(10).join('• ' + req for req in data.get('requirements', []))}

**Entry Points:**
• E-visa: 28 designated airports
• Regular visa: All entry points

⚠️ Some areas require special permits."""
        
        elif destination == "schengen":
            return f"""🇪🇺 **Schengen Visa Requirements**

**Visa-Free Countries ({data.get('duration', '90 days')}):**
• US, UK, Canada, Australia, Japan, South Korea

**Visa Required:**
• China, India, Russia, Philippines, Thailand

**Requirements:**
• {chr(10).join('• ' + req for req in data.get('requirements', []))}

**Application:**
• Processing: {data.get('processing_time', 'N/A')}
• Cost: {data.get('cost', 'N/A')}
• Apply at embassy of main destination country

⚠️ Check specific country embassy requirements."""
        
        return "Sorry, I don't have information for that destination yet."
    
    def get_capabilities(self) -> List[str]:
        """Return visa agent capabilities"""
        return [
            "Visa requirements analysis",
            "Documentation guidance",
            "Processing time estimation",
            "Cost information",
            "Country-specific regulations",
            "Application procedures",
            "Embassy information"
        ]
    
    async def _generate_ai_response_new(self, destination: str, nationality: str) -> Dict:
        """Generate AI-powered visa response for new project"""
        prompt = f"""You are a Visa Requirements Specialist for HOT Travel Assistant.

Destination: {destination}
Traveler Nationality: {nationality}

Please provide comprehensive visa information including:
1. Whether a visa is required for {nationality} citizens traveling to {destination}
2. Visa-free options if available  
3. Required documents
4. Processing times and costs
5. Important notes and warnings

Format your response as structured data that can be easily processed.
Always remind users to verify with official sources."""

        response = await self.model.generate_content_async(prompt)
        
        return {
            "visa_required": "check_required",
            "ai_response": response.text,
            "mode": "ai_powered"
        }
    
    def _generate_fallback_response_new(self, destination: str, nationality: str) -> Dict:
        """Generate fallback response using hardcoded data for new project"""
        visa_info = self.visa_data.get(destination, {})
        
        if not visa_info:
            return {
                "visa_required": "unknown",
                "message": f"Visa information not available for {destination}",
                "recommendation": "Please check with the embassy or consulate"
            }
        
        # Simple logic for visa requirements
        visa_free_countries = visa_info.get("visa_free", [])
        visa_required_countries = visa_info.get("visa_required", [])
        
        if nationality in visa_free_countries:
            visa_required = False
        elif nationality in visa_required_countries:
            visa_required = True
        else:
            visa_required = "check_required"
        
        return {
            "visa_required": visa_required,
            "duration": visa_info.get("duration", "Unknown"),
            "requirements": visa_info.get("requirements", []),
            "processing_time": visa_info.get("processing_time", "Unknown"),
            "cost": visa_info.get("cost", "Unknown"),
            "mode": "database_lookup"
        }