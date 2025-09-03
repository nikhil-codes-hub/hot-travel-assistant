from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from config.database import get_db
from models.database_models import UserProfile
import hashlib
import os
import structlog
import io
from contextlib import redirect_stdout
from playwright.async_api import async_playwright
import json
import asyncio

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
except ImportError:
    vertexai = None
    GenerativeModel = None

logger = structlog.get_logger()

class HotDealsAgent(BaseAgent):
    def __init__(self):
        super().__init__("HotDealsAgent")
        self.ai_model = self._initialize_ai_model()
    
    async def execute(self, session_id: str, query: str = None) -> Dict[str, Any]:
        """Execute HOT deals that matching user's query"""
        
        # Try AI response first if available
        if self.ai_model:
            try:
                response = await self._generate_hot_deals(query)
            except Exception as e:
                logger.error(f"Hot Deals Agent AI error: {e}")

        return self.format_output({
            "hot_deals": response,
            "disclaimer": "Always consult a qualified medical professional for personalized travel health advice."
        })

    async def _scrape_houseoftravel_deals():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://www.houseoftravel.co.nz/deals/search", timeout=60000)
            await page.wait_for_selector("div", timeout=30000)

            # Use a more robust selector for the deal cards
            deal_cards = await page.query_selector_all("div._deal-card")
            results = []

            for i, card in enumerate(deal_cards, start=1):
                # Using more specific and resilient selectors based on the provided HTML structure
                title_element = await card.query_selector("xpath=.//div[2]/div[2]/h3")
                airline_element = await card.query_selector("xpath=.//span[contains(text(), 'Flying with')]/following-sibling::span[2]")
                price_element = await card.query_selector("xpath=.//span[contains(@class, '_heading-3') or contains(@class, '_heading-2')]")
                destination_element = await card.query_selector("xpath=.//div[2]/div[1]/span")
                info_element = await card.query_selector("xpath=.//div[2]/div[4]")

                deal = {
                    "title": (await title_element.inner_text()) if title_element else None,
                    "airline": (await airline_element.inner_text()) if airline_element else None,
                    "price": (await price_element.inner_text()) if price_element else None,
                    "destination": (await destination_element.inner_text()) if destination_element else None,
                    "info": (await info_element.inner_text()) if info_element else None,
                }
                if title_element and airline_element and price_element and destination_element and info_element:
                    results.append(deal)

            await browser.close()
            return results

    def _initialize_ai_model(self):
        """Initialize Vertex AI model for extract deals if available"""
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

            if project_id and vertexai:
                vertexai.init(project=project_id, location=location)
                model = GenerativeModel(model_name)
                logger.info(f"✅ {self.name}: Vertex AI initialized: {project_id} - {model_name}")
                return model
            else:
                logger.info(f"ℹ️ {self.name}: Using fallback mode (no AI)")
                return None
        except Exception as e:
            logger.error(f"❌ {self.name}: Failed to initialize Vertex AI: {e}")
            return None

    async def _generate_hot_deals(self, query: str = None) -> Dict[str, Any]:
        """Generate AI-powered deals information"""
        
        # Get hot deals
        hot_deals = await self._scrape_houseoftravel_deals()

        # Create system prompt
        prompt = f"""
You are an expert at extracting travel deal information from a given list of deals , which is {hot_deals}

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
        
        response = await self.ai_model.generate_content_async(prompt)
        
        return {
            "status": "success",
            "type": "personalized",
            "analysis": response.text,
            "data_source": "ai_powered"
        }