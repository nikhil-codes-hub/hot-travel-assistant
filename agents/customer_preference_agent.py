"""
Agent for analyzing customer travel data to provide preferences and recommendations.
"""
import logging
import os
import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, List
import io
from contextlib import redirect_stdout

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
except ImportError:
    vertexai = None
    GenerativeModel = None

from .base_agent import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)

class CustomerPreferenceAgent(BaseAgent):
    """Agent for analyzing customer travel preferences and providing recommendations."""

    def __init__(self, db_path: str = "customer_travel.db"):
        super().__init__(
            name="Customer Preference Agent",
            description="Analyzes customer travel history to identify preferences, habits, and provide personalized recommendations."
        )
        self.db_path = db_path
        self.table_name = "customerdata"
        self.df = None

        try:
            conn = sqlite3.connect(db_path)
            # Load data from SQLite into a pandas DataFrame
            self.df = pd.read_sql_query(f"SELECT * FROM {self.table_name}", conn)
            conn.close()

            # Convert date columns to datetime objects for better analysis
            self.df['booking_date'] = pd.to_datetime(self.df['booking_date'])
            self.df['departure_date'] = pd.to_datetime(self.df['departure_date'])
            logger.info(f"✅ {self.name}: Data loaded from SQLite DB at {db_path}.")
        except sqlite3.OperationalError as e:
            logger.error(f"❌ {self.name}: SQLite error: {e}. Did you run the script to create the database?")
        except FileNotFoundError:
            logger.error(f"❌ {self.name}: Database file not found at {db_path}")
        except Exception as e:
            logger.error(f"❌ {self.name}: Error loading data: {e}")

        self.model = self._initialize_ai_model()

    def _initialize_ai_model(self):
        """Initialize Vertex AI model if available and authorized."""
        if self.df is None:
            logger.warning(f"⚠️ {self.name}: Skipping AI model initialization because data is not loaded.")
            return None
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

    async def can_handle(self, query: str) -> bool:
        """Determines if the agent can handle the given query based on keywords."""
        if self.model is None or self.df is None:
            return False

        # Expanded keywords to better catch preference and recommendation queries
        keywords = [
            "customer", "traveler", "pattern",
            "trend", "habit", "popular", "nationality", "age", "cabin class",
            "booking", "destination", "departure", "how many", "which country", "compare",
            "show me data", "statistics", "preference", "recommend", "suggestion",
            "suggest", "recommendation", "history", "choice",
        ]
        return any(keyword in query.lower() for keyword in keywords)

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Processes the query by analyzing the customer travel data."""
        if self.model is None or self.df is None:
            return AgentResponse(
                response="I am sorry, but the customer data analysis service is currently unavailable.",
                agent_type=self.agent_type,
                confidence=0.9, 
                metadata={"source": self.db_path, "status": "unavailable"}
            )

        logger.info(f"{self.name}: Processing query: {query}")

        try:
            return await self._generate_ai_response(query, context)
        except Exception as e:
            logger.error(f"❌ {self.name}: Error processing query: {e}")
            return AgentResponse(
                response=f"I encountered an error while analyzing the data: {e}",
                agent_type=self.agent_type,
                confidence=0.5,
                metadata={"error": str(e)}
            )

    async def _generate_ai_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Generate AI-powered analysis of the dataframe."""

        # Capture dataframe info and head for the prompt
        with io.StringIO() as buf, redirect_stdout(buf):
            self.df.info()
            df_info = buf.getvalue()

        df_head = self.df.head().to_markdown()

        # Dynamically create prompt instructions based on context
        traveler_name = context.get("traveler_name") if context else None
        traveler_email = context.get("traveler_email") if context else None
        user_history_df = None
        prompt_instruction = ""
        identifier = ""

        if traveler_name:
            identifier = f"traveler_name: '{traveler_name}'"
            # Use case-insensitive search for the traveler's name
            user_history_df = self.df[self.df['Traveler_name'].str.contains(traveler_name, case=False, na=False)]
        elif traveler_email:
            identifier = f"traveler_email: '{traveler_email}'"
            # Use case-insensitive exact match for the traveler's email
            user_history_df = self.df[self.df['Traveler_Email'].str.lower() == traveler_email.lower()]

        if user_history_df is not None and not user_history_df.empty:
            # Extract the traveler's name from the retrieved data to personalize the greeting.
            traveler_name_from_df = user_history_df['Traveler_name'].iloc[0]
            user_history_md = user_history_df.to_markdown(index=False)
            prompt_instruction = f"""
**Personalized Request for {traveler_name_from_df} (identified by {identifier})**
This is a request for a specific user. Your task is to act as their personal travel consultant.
- **Address the user by their name, {traveler_name_from_df}.**
- Analyze their travel history provided below to give a personalized answer.
- If the user asks for a recommendation, suggest a trip based on their frequent destinations, cabin class, and booking patterns. Explain WHY you are making the suggestion based on their history.

**User's Travel History:**
```
{user_history_md}
```
"""
        else:
            # This branch handles both "no user_id" and "user_id not found"
            prompt_instruction = """
**General Request**
This is a general query, not for a specific user, or for a user with no travel history.
Analyze the entire dataset to answer the query.
If the user asks for a recommendation (e.g., "suggest a trip"), you MUST analyze the full dataset to find the most popular destinations or travel trends and base your recommendation on that analysis.
"""

        prompt = f"""You are a helpful and friendly travel assistant for HOT Travel. Your special skill is analyzing travel data from a pandas DataFrame named `df` to understand customer preferences and make smart recommendations.
The DataFrame contains customer travel booking data.

**Analysis Task:**
{prompt_instruction}

**Full DataFrame Schema:**
```
{df_info}
```

**First 5 Rows of the Full Dataset:**
{df_head}

**User Query:**
"{query}"

Based on your task (Personalized or General) and the data provided, generate a concise and helpful answer.
Write your response in simple, plain English that a customer can easily understand, avoiding technical jargon.
When providing a recommendation, you MUST explain your reasoning by referencing the specific data patterns you found (e.g., "Based on your frequent business class travel...").
Format your response clearly using markdown and bullet points for lists.
If the query cannot be answered with the provided data, politely state that.
"""
        response = await self.model.generate_content_async(prompt)

        suggestions = [
            "What is the most popular destination overall?",
            "Destination you like to visit"
            "Preferred Cabin Class.",
            "Suggest a trip for a family of 4."
        ]

        return AgentResponse(
            response=response.text,
            suggestions=suggestions,
            agent_type=self.agent_type,
            confidence=0.85,
            metadata={"source": self.db_path, "mode": "ai"}
        )

    def get_info(self) -> Dict[str, Any]:
        """Returns information about the agent."""
        return {
            "name": self.name,
            "description": self.description, 
            "data_source": self.db_path,
            "data_shape": self.df.shape if self.df is not None else "N/A",
            "status": "active" if self.model is not None and self.df is not None else "inactive"
        }

    def get_capabilities(self) -> List[str]:
        """Return agent capabilities."""
        return [
            "Analyze my travel history for suggestions.",
            "Find popular travel destinations and trends.",
            "Get personalized trip recommendations.",
            "Ask questions about general travel patterns."
        ]
