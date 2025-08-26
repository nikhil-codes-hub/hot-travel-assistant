"""
Agent for analyzing customer travel data to provide preferences and recommendations.
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional

from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)

class CustomerPreferenceAgent(BaseAgent):
    """Agent for analyzing customer travel preferences and providing recommendations."""

    def __init__(self, csv_path: str = "customer_travel_dataset.csv"):
        super().__init__()
        self.name = "CustomerPreferenceAgent"
        self.description = "Analyzes customer travel history to identify preferences, habits, and provide personalized recommendations."
        
        try:
            self.df = pd.read_csv(csv_path)
            # Convert date columns to datetime objects for better analysis
            self.df['booking_date'] = pd.to_datetime(self.df['booking_date'])
            self.df['departure_date'] = pd.to_datetime(self.df['departure_date'])
            
            # Initialize the LLM for the pandas agent
            llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
            
            # Add a prefix to the prompt to guide the agent's behavior for providing recommendations.
            # This helps the LLM understand its role better.
            agent_prefix = """
You are working with a pandas dataframe in Python. The name of the dataframe is `df`.
The dataframe contains customer travel booking data.
When asked for recommendations or suggestions, you should analyze the user's travel history
(if a user is specified by name or ID) or general travel patterns in the dataset.
Provide a concise, helpful answer, and if you are providing a list, format it nicely.
"""
            # Create the pandas dataframe agent. This agent is specialized to work with dataframes.
            self.agent = create_pandas_dataframe_agent(
                llm,
                self.df,
                verbose=True,
                agent_type="zero-shot-react-description",
                prefix=agent_prefix,
                agent_executor_kwargs={"handle_parsing_errors": True}
            )
            logger.info("✅ Customer Preference Agent: Initialized and data loaded.")
        except FileNotFoundError:
            logger.error(f"❌ Customer Preference Agent: Data file not found at {csv_path}")
            self.df = None
            self.agent = None
        except Exception as e:
            logger.error(f"❌ Customer Preference Agent: Error during initialization: {e}")
            self.df = None
            self.agent = None

    async def can_handle(self, query: str) -> bool:
        """Determines if the agent can handle the given query based on keywords."""
        if self.agent is None:
            return False
            
        # Expanded keywords to better catch preference and recommendation queries
        keywords = [
            "analyze", "analysis", "customer", "traveler", "pattern",
            "trend", "habit", "popular", "nationality", "age", "cabin class",
            "booking", "destination", "departure", "how many", "which country", "compare",
            "show me data", "statistics", "preference", "recommend", "suggestion",
            "suggest", "recommendation", "history", "choice"
        ]
        return any(keyword in query.lower() for keyword in keywords)

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Processes the query by analyzing the customer travel data."""
        if self.agent is None:
            return AgentResponse(
                response="I am sorry, but the customer preference data is currently unavailable for analysis.",
                agent_type=self.name,
                confidence=0.9
            )
            
        logger.info(f"Customer Preference Agent: Processing query: {query}")
        
        full_query = query
        # You could add more sophisticated context handling here in a real application
        # For now, the agent is smart enough to handle queries like "preferences for traveler ID 596"
        
        try:
            # Use ainvoke for asynchronous execution, which is better for server environments.
            result = await self.agent.ainvoke({"input": full_query})
            answer = result.get("output", "I was unable to process the analysis request.")

            return AgentResponse(
                response=answer,
                agent_type=self.name,
                confidence=0.9,
                metadata={"source": "customer_travel_dataset.csv"}
            )
        except Exception as e:
            logger.error(f"❌ Customer Preference Agent: Error processing query: {e}")
            return AgentResponse(
                response=f"I encountered an error while analyzing the data: {e}",
                agent_type=self.name,
                confidence=0.5
            )

    def get_info(self) -> Dict[str, Any]:
        """Returns information about the agent."""
        return {
            "name": self.name,
            "description": self.description,
            "data_source": "customer_travel_dataset.csv",
            "data_shape": self.df.shape if self.df is not None else "N/A",
            "status": "active" if self.agent is not None else "inactive"
        }
