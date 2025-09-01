"""
Hot Deals Agent

Specialized agent for finding deal offers on https://www.houseoftravel.co.nz/deals.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from .base_agent import BaseAgent, AgentResponse
import vertexai, json, asyncio
from langchain_google_vertexai import ChatVertexAI
from scrapegraphai.graphs import SmartScraperGraph



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
            
            if project_id and vertexai and ChatVertexAI:
                vertexai.init(project=project_id, location=location)

                # Use the LangChain wrapper for Vertex AI for compatibility with scrapegraphai
                model = ChatVertexAI(model_name=model_name, temperature=0)
                logger.info(f"✅ Hot Deals Agent: LangChain Vertex AI model initialized: {project_id} - {model_name}")
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
            # The user's query is used to refine the scraping prompt.
            prompt = f"""
You are an expert at extracting travel deal information from web pages.
Your goal is to extract all available deals that match the user's query: "{query}".

For each deal you find, please extract the following details and structure them into a JSON object:
- title: The name of the travel package.
- destination: The primary destination (city or country or region or island).
- duration: The number of nights or days.
- price: The total price or per person.
- flying_with: The airline flying with, if mentioned.

Please return a JSON object with a single key "deals" which contains a list of up to five these deal objects.
Please return the deals with complete information , title, destination, price, flying_with
"""

            graph_config = {
                "llm": {
                    "model_instance": self.model,
                    # Add model_tokens to fix 'model_tokens not specified' error with scrapegraphai
                    "model_tokens": 8192,
                },
            }

            scraper_graph = SmartScraperGraph(
                prompt=prompt,
                source="https://www.houseoftravel.co.nz/deals/search",
                config=graph_config
            )

            # Use asyncio.to_thread to run the synchronous `run` method in a separate thread,
            # preventing it from blocking the main async event loop.
            # This is necessary because scrapegraphai's SmartScraperGraph does not have an `arun` method.
            result = await asyncio.to_thread(scraper_graph.run)

            response_text = json.dumps(result, indent=2)

            return AgentResponse(
                response=f"I found the following deals for you:\n\n```json\n{response_text}\n```",
                suggestions=[
                    "Find a deals from London to New York tomorrow",
                    "What are the cheapest deals to Paris next month?",
                    "Book a holiday deal in September"
                ],
                agent_type=self.agent_type,
                confidence=0.9,
                metadata={"mode": "ai", "model": "scrapegraphai_vertex"}
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