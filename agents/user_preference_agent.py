import logging
from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Any

from .base_agent import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class UserPreferenceAgent(BaseAgent):
    """
    Analyzes user's historical bookings to suggest future travel preferences.
    """

    def __init__(self, decay_rate: float = 0.01):
        """
        Initializes the agent.
        Args:
            decay_rate: Controls how quickly older bookings lose importance.
                        Higher value means faster decay.
        """
        super().__init__(
            name="User Preference Analyzer",
            description="Analyzes user booking history to predict future travel preferences using a time-decay model."
        )
        self.decay_rate = decay_rate
        # In a real scenario, user data would be fetched from a database.
        # For this example, we'll use mock data passed in the context.

    async def can_handle(self, query: str) -> bool:
        """Check if the query is a request for travel suggestions."""
        query_lower = query.lower()
        suggestion_keywords = [
            "suggest a trip", "recommend a flight", "what's next",
            "plan for me", "my usual trip", "next vacation"
        ]
        return any(keyword in query_lower for keyword in suggestion_keywords)

    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Processes the query to suggest a trip based on historical data.
        """
        logger.info(f"User Preference Agent processing: {query}")

        if not context or "user_history" not in context:
            return AgentResponse(
                response="I don't have your booking history. To get personalized suggestions, please book a flight with us first!",
                suggestions=["Find flights from NYC to LAX", "Book a trip to Japan"],
                agent_type=self.agent_type,
                confidence=0.6,
                metadata={"mode": "no_history"}
            )

        user_history = context["user_history"]
        if not user_history:
             return AgentResponse(
                response="Your booking history is empty. I can't make a suggestion yet.",
                suggestions=["Find flights from NYC to LAX", "Book a trip to Japan"],
                agent_type=self.agent_type,
                confidence=0.6,
                metadata={"mode": "no_history"}
            )

        try:
            prediction = self._predict_from_history(user_history)

            if not prediction['departureLocation'] or not prediction['destinationLocation']:
                 return AgentResponse(
                    response="I couldn't determine a likely next trip from your history. Where would you like to go?",
                    suggestions=["Flights to Tokyo", "Business class to London"],
                    agent_type=self.agent_type,
                    confidence=0.5,
                    metadata={"mode": "prediction_failed"}
                )

            response_text = (
                f"✈️ **Personalized Suggestion For You**\n\n"
                f"Based on your travel history, I think you might be interested in a trip:\n\n"
                f"• **From**: {prediction['departureLocation']}\n"
                f"• **To**: {prediction['destinationLocation']}\n"
                f"• **Cabin Class**: {prediction['cabinClass']}\n\n"
                f"Would you like me to look for flights for this route?"
            )

            suggestions = [
                f"Yes, find flights from {prediction['departureLocation']} to {prediction['destinationLocation']}",
                "Suggest another destination",
                "How about a different cabin class?"
            ]

            return AgentResponse(
                response=response_text,
                suggestions=suggestions,
                agent_type=self.agent_type,
                confidence=0.85,
                metadata={"mode": "prediction", "prediction": prediction}
            )
        except Exception as e:
            logger.error(f"User Preference Agent error: {e}")
            return AgentResponse(
                response="I had trouble analyzing your preferences. Please try asking in a different way.",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"error": str(e)}
            )

    # Add Seasonal Weighting
    def _seasonal_boost(self, booking_date: datetime) -> float:
        current_month = datetime.now(timezone.utc).month
        booking_month = booking_date.month

        # Define seasons (Northern Hemisphere example)
        def get_season(month):
            if month in [12, 1, 2]:
                return 'winter'
            elif month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            else:
                return 'autumn'

        if get_season(current_month) == get_season(booking_month):
            return 1.2  # Boost for same-season bookings
        return 1.0


    def _time_decay_weight(self, booking_date: datetime) -> float:
        """
        Calculates a weight for a booking based on its recency.
        Uses exponential decay: weight = exp(-decay_rate * days_ago)
        """
        days_ago = (datetime.now(timezone.utc) - booking_date).days
        base_weight = math.exp(-self.decay_rate * days_ago)
        return base_weight * self._seasonal_boost(booking_date)


    def _predict_from_history(self, history: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """
        Analyzes booking history with time decay to predict the next trip.
        """
        preferences = {
            "departureLocation": {},
            "destinationLocation": {},
            "cabinClass": {}
        }

        for booking in history:
            try:
                # Assuming booking_date is in ISO format string.
                # The 'Z' suffix for UTC is not supported by fromisoformat() in Python < 3.11.
                booking_date = datetime.fromisoformat(booking["booking_date"].replace('Z', '+00:00'))
                weight = self._time_decay_weight(booking_date)

                for key in preferences.keys():
                    value = booking.get(key)
                    if value:
                        preferences[key][value] = preferences[key].get(value, 0) + weight
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Skipping invalid booking in history: {booking}. Error: {e}")
                continue

        prediction = {}
        for key, value_weights in preferences.items():
            if not value_weights:
                prediction[key] = None
            else:
                # Get the item with the highest score
                prediction[key] = max(value_weights, key=value_weights.get)

        return prediction

    def get_capabilities(self) -> List[str]:
        """Return agent capabilities."""
        return [
            "Personalized travel suggestions",
            "User booking history analysis",
            "Time-decay based preference prediction",
            "Suggests departure, destination, and cabin class"
        ]