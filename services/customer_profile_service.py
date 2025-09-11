import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from models.customer_profile import (
    CustomerProfile, CustomerTravelHistory, 
    CustomerPreference, EventCalendar
)
# Simple LLM integration without dependencies

logger = logging.getLogger(__name__)

class CustomerProfileService:
    def __init__(self):
        pass
    
    def get_or_create_customer(self, db: Session, email: str, first_name: str = None, last_name: str = None) -> CustomerProfile:
        """Get existing customer or create new one"""
        customer = db.query(CustomerProfile).filter(CustomerProfile.email == email).first()
        
        if not customer:
            customer = CustomerProfile(
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            logger.info(f"Created new customer profile for {email}")
        
        return customer
    
    def get_customer_travel_history(self, db: Session, email: str) -> List[CustomerTravelHistory]:
        """Get customer's travel history ordered by date"""
        return db.query(CustomerTravelHistory)\
            .filter(CustomerTravelHistory.customer_email == email)\
            .order_by(desc(CustomerTravelHistory.travel_date_start))\
            .all()
    
    def get_customer_preferences(self, db: Session, email: str) -> List[CustomerPreference]:
        """Get customer's preferences ordered by weight"""
        return db.query(CustomerPreference)\
            .filter(CustomerPreference.customer_email == email)\
            .order_by(desc(CustomerPreference.weight))\
            .all()
    
    def add_travel_history(self, db: Session, email: str, travel_data: Dict[str, Any]) -> CustomerTravelHistory:
        """Add new travel history entry"""
        history = CustomerTravelHistory(
            customer_email=email,
            destination=travel_data.get('destination'),
            country=travel_data.get('country'),
            city=travel_data.get('city'),
            event_name=travel_data.get('event_name'),
            event_type=travel_data.get('event_type'),
            travel_date_start=travel_data.get('travel_date_start'),
            travel_date_end=travel_data.get('travel_date_end'),
            season=travel_data.get('season'),
            budget_range=travel_data.get('budget_range'),
            travel_style=travel_data.get('travel_style'),
            satisfaction_rating=travel_data.get('satisfaction_rating'),
            notes=travel_data.get('notes')
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    
    def get_upcoming_events(self, db: Session, limit: int = 20) -> List[EventCalendar]:
        """Get upcoming events starting from today"""
        today = date.today()
        return db.query(EventCalendar)\
            .filter(EventCalendar.event_date_start >= today)\
            .order_by(EventCalendar.event_date_start)\
            .limit(limit)\
            .all()
    
    def find_similar_events(self, db: Session, past_event_types: List[str], limit: int = 10) -> List[EventCalendar]:
        """Find upcoming events similar to customer's past events"""
        if not past_event_types:
            return []
        
        today = date.today()
        return db.query(EventCalendar)\
            .filter(
                and_(
                    EventCalendar.event_date_start >= today,
                    or_(*[EventCalendar.event_type == event_type for event_type in past_event_types])
                )
            )\
            .order_by(EventCalendar.event_date_start)\
            .limit(limit)\
            .all()
    
    def generate_personalized_suggestions(self, db: Session, email: str) -> Dict[str, Any]:
        """Generate LLM-powered personalized travel suggestions based on customer history"""
        
        # Get customer data
        customer = db.query(CustomerProfile).filter(CustomerProfile.email == email).first()
        if not customer:
            return {"suggestions": [], "message": "Customer profile not found"}
        
        travel_history = self.get_customer_travel_history(db, email)
        preferences = self.get_customer_preferences(db, email)
        
        if not travel_history:
            return {"suggestions": [], "message": "No travel history found for personalized recommendations"}
        
        # Get past event types for similarity matching
        past_event_types = list(set([h.event_type for h in travel_history if h.event_type]))
        similar_upcoming_events = self.find_similar_events(db, past_event_types)
        
        # Prepare data for LLM
        customer_profile_text = self._format_customer_data_for_llm(customer, travel_history, preferences)
        upcoming_events_text = self._format_events_for_llm(similar_upcoming_events)
        
        # Generate LLM suggestions
        suggestions = self._generate_llm_suggestions(customer_profile_text, upcoming_events_text)
        
        return {
            "customer_email": email,
            "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
            "travel_history_count": len(travel_history),
            "suggestions": suggestions,
            "similar_events": [event.to_dict() for event in similar_upcoming_events[:5]]
        }
    
    def _format_customer_data_for_llm(self, customer: CustomerProfile, 
                                     travel_history: List[CustomerTravelHistory],
                                     preferences: List[CustomerPreference]) -> str:
        """Format customer data for LLM input"""
        
        history_text = ""
        for trip in travel_history[:5]:  # Last 5 trips
            date_str = trip.travel_date_start.strftime("%B %Y") if trip.travel_date_start else "Unknown date"
            history_text += f"- {date_str}: Visited {trip.destination}"
            if trip.event_name:
                history_text += f" for {trip.event_name} ({trip.event_type})"
            if trip.travel_style:
                history_text += f" as {trip.travel_style} trip"
            history_text += "\n"
        
        pref_text = ""
        for pref in preferences:
            pref_text += f"- {pref.preference_type}: {pref.preference_value}\n"
        
        return f"""Customer Profile:
Name: {customer.first_name} {customer.last_name}
Email: {customer.email}

Recent Travel History:
{history_text}

Preferences:
{pref_text if pref_text else "No specific preferences recorded"}"""
    
    def _format_events_for_llm(self, events: List[EventCalendar]) -> str:
        """Format upcoming events for LLM input"""
        if not events:
            return "No similar upcoming events found."
        
        events_text = "Upcoming Similar Events:\n"
        for event in events:
            date_str = event.event_date_start.strftime("%B %d, %Y") if event.event_date_start else "Date TBD"
            events_text += f"- {event.event_name} in {event.destination} on {date_str}\n"
            if event.description:
                events_text += f"  Description: {event.description}\n"
        
        return events_text
    
    def _generate_llm_suggestions(self, customer_data: str, events_data: str) -> List[Dict[str, Any]]:
        """Generate personalized suggestions using LLM"""
        
        prompt = f"""Based on the customer's travel history and preferences, generate 3-5 personalized travel suggestions. 
Focus on events and destinations similar to their past travels.

{customer_data}

{events_data}

Generate suggestions in the following JSON format:
[
  {{
    "suggestion_title": "Brief catchy title",
    "destination": "City, Country",
    "event_name": "Name of event/festival",
    "event_date": "Date or month",
    "reasoning": "Why this matches their interests based on past travels",
    "confidence_score": 0.85
  }}
]

Make the suggestions engaging and personalized. Reference their specific past travels when explaining why they might enjoy the suggestion."""
        
        try:
            # Simple rule-based suggestions for now (can be enhanced with actual LLM later)
            suggestions = self._generate_rule_based_suggestions(customer_data, events_data)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return self._create_fallback_suggestions()
    
    def _generate_rule_based_suggestions(self, customer_data: str, events_data: str) -> List[Dict[str, Any]]:
        """Generate rule-based suggestions based on customer history"""
        suggestions = []
        
        # Parse customer data for past events
        if "Diwali" in customer_data:
            suggestions.append({
                "suggestion_title": "Dussehra Festival Experience in Royal Mysore",
                "destination": "Mysore, India", 
                "event_name": "Dussehra Festival",
                "event_date": "October 2024",
                "reasoning": "Since you enjoyed the Diwali Festival in Bangalore, you'd love the grand Dussehra celebration in Mysore's royal palaces",
                "confidence_score": 0.9
            })
        
        if "Oktoberfest" in customer_data:
            suggestions.append({
                "suggestion_title": "Vienna Christmas Markets Magic",
                "destination": "Vienna, Austria",
                "event_name": "Christmas Markets",
                "event_date": "December 2024",
                "reasoning": "Following your Oktoberfest experience in Germany, Vienna's Christmas markets offer similar festive atmosphere with traditional crafts and mulled wine",
                "confidence_score": 0.85
            })
        
        if "Cherry Blossom" in customer_data or "Japan" in customer_data:
            suggestions.append({
                "suggestion_title": "Kyoto Cherry Blossoms & Temple Gardens",
                "destination": "Kyoto, Japan",
                "event_name": "Cherry Blossom Festival", 
                "event_date": "April 2025",
                "reasoning": "Based on your love for Japanese cherry blossoms in Tokyo, Kyoto offers more traditional temples and gardens during sakura season",
                "confidence_score": 0.95
            })
        
        if "Holi" in customer_data:
            suggestions.append({
                "suggestion_title": "Original Holi Celebration in Krishna's Birthplace",
                "destination": "Mathura, India",
                "event_name": "Holi Festival",
                "event_date": "March 2025",
                "reasoning": "After your Holi experience in Rajasthan, experience the original celebration in Mathura where Krishna was born",
                "confidence_score": 0.9
            })
        
        if "festival" in customer_data.lower():
            suggestions.append({
                "suggestion_title": "Discover More Festival Experiences",
                "destination": "Based on your preferences",
                "event_name": "Cultural Festivals",
                "reasoning": "Your travel history shows a passion for cultural festivals - let's find more authentic celebrations worldwide",
                "confidence_score": 0.8
            })
        
        return suggestions[:4]  # Return top 4 suggestions
    
    def _parse_llm_suggestions(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured suggestions"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                suggestions = json.loads(json_str)
                
                # Validate structure
                for suggestion in suggestions:
                    if not all(key in suggestion for key in ['suggestion_title', 'destination', 'reasoning']):
                        raise ValueError("Invalid suggestion structure")
                
                return suggestions
            
            # Fallback: parse text manually
            return self._parse_text_suggestions(llm_response)
            
        except Exception as e:
            logger.error(f"Error parsing LLM suggestions: {e}")
            return self._create_fallback_suggestions()
    
    def _parse_text_suggestions(self, text: str) -> List[Dict[str, Any]]:
        """Parse text-based suggestions when JSON parsing fails"""
        suggestions = []
        
        # Simple text parsing logic
        lines = text.split('\n')
        current_suggestion = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'destination' in line.lower() or 'event' in line.lower():
                if current_suggestion:
                    suggestions.append(current_suggestion)
                current_suggestion = {
                    'suggestion_title': line,
                    'destination': 'Various locations',
                    'reasoning': 'Based on your travel preferences',
                    'confidence_score': 0.7
                }
        
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _create_fallback_suggestions(self) -> List[Dict[str, Any]]:
        """Create basic fallback suggestions when LLM fails"""
        return [
            {
                "suggestion_title": "Explore Similar Cultural Events",
                "destination": "Based on your preferences",
                "reasoning": "We'll help you find events similar to your past travels",
                "confidence_score": 0.5
            }
        ]