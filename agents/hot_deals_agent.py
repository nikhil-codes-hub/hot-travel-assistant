"""
Hot Deals Agent

Specialized agent for finding deal offers on https://www.houseoftravel.co.nz/deals.
"""

import logging
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from .base_agent import BaseAgent, AgentResponse
import vertexai
from vertexai.generative_models import GenerativeModel, FunctionDeclaration, Tool, Part
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info



logger = logging.getLogger(__name__)


class HotDealsAgent(BaseAgent):
    """
   Hot Deals Agent for finding deal offers on https://www.houseoftravel.co.nz/deals
    """
    
    def __init__(self):
        super().__init__(
            name="Hot Deals Assistant",
            description="Finds deal offers on https://www.houseoftravel.co.nz/deals."
        )
        self.model = self._initialize_ai_model()


    def _initialize_ai_model(self):
        """Initialize Vertex AI model with Hot Deals."""

        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            
            if project_id and vertexai:
                vertexai.init(project=project_id, location=location)

                system_instruction = """ You are a deals details extraction and search assistant.
                The following data was extracted from a travel deals webpage. 
                Validate and structure it into a clean JSON format with the following keys for each deal:
                - title: Package name
                - destination: Destination country/city
                - duration: Number of nights
                - inclusions: List of inclusions (e.g., flights, meals, transfers)
                - price: Price per person
                - promotional_tag: Any promotional labels (e.g., 'HOT EXCLUSIVE')
                - flying_with: Airline if mentioned

                Output only JSON without additional explanations."""

                model = GenerativeModel(model_name, system_instruction=system_instruction, generation_config = {"temperature": 0} )
                logger.info(f"✅ Hot Deals Agent: Vertex AI initialized: {project_id} - {model_name}")
                return model
            else:
                logger.info("ℹ️ Hot Deals Agent: Using fallback mode (no AI or required libraries).")
                return None
        except Exception as e:
            logger.error(f"❌ Hot Deals Agent: Failed to initialize Vertex AI: {e}")
            return None
    
    async def can_handle(self, query: str) -> bool:
        """Check if query is deals-related."""
        query_lower = query.lower()
        flight_keywords = [
            "deals", "destination", "holiday"
        ]
        # A simple check to see if it looks like a flight query
        return sum(keyword in query_lower for keyword in flight_keywords) >= 1
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process deals-related query using AI model."""
        logger.info(f"Hot Deals Agent processing: {query}")
        
        if not self.model:
            return AgentResponse(
                response="I'm sorry, the Hot deals service is currently unavailable. Please check my configuration.",
                agent_type=self.agent_type,
                confidence=0.2,
                metadata={"mode": "unavailable", "reason": "AI model not initialized."}
            )

        try:
            return await self._generate_ai_response(query)
        except Exception as e:
            logger.error(f"Hot Deals Agent AI error: {e}")
            return AgentResponse(
                response="Sorry, I encountered an error trying to find deals for you.",
                agent_type=self.agent_type,
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    async def _generate_ai_response(self, query: str) -> AgentResponse:
        """Generate AI-powered response by calling scrapegraph."""
        try:
            # Generate initial response
            scraper_graph = SmartScraperGraph(
                prompt="Extract all hot travel deals with details.",
                source="https://www.houseoftravel.co.nz/deals",
                config={
                    "llm": {
                        "provider": "custom",   # tells ScrapeGraph we are injecting a model
                        "custom_llm": self.model
                    }
                },
            )
            result = scraper_graph.run()

            return AgentResponse(
                response=prettify_exec_info(result),
                suggestions=[
                    "Find a deals from London to New York tomorrow",
                    "What are the cheapest deals to Paris next month?",
                    "Book a holiday deal in September"
                ],
                agent_type=self.agent_type,
                confidence=0.9,
                metadata={"mode": "ai", "model": "vertex_ai"}
            )

        except Exception as e:
            logger.error(f"Error in AI response generation: {e}")
            return AgentResponse(
                response="Sorry, I encountered an error processing your Hot Deals request.",
                agent_type=self.agent_type,
                confidence=0.1,
                metadata={"error": str(e)}
            )

    
    def get_capabilities(self) -> List[str]:
        """Return Hot Deals offer agent capabilities."""
        return [
            "Hot deals search",
            "Pretty output format",
            "Extracted from a travel deals webpage"
        ]