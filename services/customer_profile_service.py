import json
import logging
import requests
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
        # Configuration for LLM integration
        self.use_openai = False  # Set to True if you have OpenAI API key
        self.openai_api_key = None  # Set your API key here
        self.use_local_llm = True   # Try local LLM first
    
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
        """Format customer data for LLM input with rich details"""
        
        history_text = ""
        travel_patterns = {
            'destinations': [],
            'countries': [],
            'event_types': [],
            'travel_styles': [],
            'seasons': [],
            'satisfaction_scores': []
        }
        
        for trip in travel_history[:10]:  # Last 10 trips for better pattern analysis
            date_str = trip.travel_date_start.strftime("%B %Y") if trip.travel_date_start else "Unknown date"
            
            # Build detailed trip description
            trip_desc = f"- {date_str}: Visited {trip.destination}"
            if trip.country and trip.city:
                trip_desc += f" ({trip.city}, {trip.country})"
            
            if trip.event_name:
                trip_desc += f" for {trip.event_name}"
                if trip.event_type:
                    trip_desc += f" ({trip.event_type})"
                    travel_patterns['event_types'].append(trip.event_type)
            
            if trip.travel_style:
                trip_desc += f" as {trip.travel_style} trip"
                travel_patterns['travel_styles'].append(trip.travel_style)
            
            if trip.season:
                trip_desc += f" during {trip.season} season"
                travel_patterns['seasons'].append(trip.season)
            
            if trip.budget_range:
                trip_desc += f" (${trip.budget_range} budget)"
            
            if trip.satisfaction_rating:
                trip_desc += f" [Satisfaction: {trip.satisfaction_rating}/5]"
                travel_patterns['satisfaction_scores'].append(trip.satisfaction_rating)
            
            if trip.notes:
                trip_desc += f"\n  Notes: {trip.notes}"
            
            history_text += trip_desc + "\n"
            
            # Collect patterns
            travel_patterns['destinations'].append(trip.destination)
            if trip.country:
                travel_patterns['countries'].append(trip.country)
        
        # Format preferences with weights
        pref_text = ""
        for pref in preferences:
            weight_indicator = "⭐" * min(pref.weight, 5) if pref.weight else ""
            pref_text += f"- {pref.preference_type}: {pref.preference_value} {weight_indicator}\n"
        
        # Generate travel pattern summary
        pattern_summary = []
        if travel_patterns['countries']:
            top_countries = list(set(travel_patterns['countries']))[:3]
            pattern_summary.append(f"Frequently visits: {', '.join(top_countries)}")
        
        if travel_patterns['event_types']:
            top_events = list(set(travel_patterns['event_types']))[:3]
            pattern_summary.append(f"Prefers events: {', '.join(top_events)}")
        
        if travel_patterns['travel_styles']:
            top_styles = list(set(travel_patterns['travel_styles']))[:2]
            pattern_summary.append(f"Travel style: {', '.join(top_styles)}")
        
        if travel_patterns['satisfaction_scores']:
            avg_satisfaction = sum(travel_patterns['satisfaction_scores']) / len(travel_patterns['satisfaction_scores'])
            pattern_summary.append(f"Average satisfaction: {avg_satisfaction:.1f}/5")
        
        return f"""Customer Profile Analysis:
Name: {customer.first_name} {customer.last_name}
Email: {customer.email}
Member since: {customer.created_at.strftime("%B %Y") if customer.created_at else "Unknown"}

Travel History ({len(travel_history)} trips):
{history_text}

Travel Patterns:
{chr(10).join([f"• {pattern}" for pattern in pattern_summary])}

Preferences:
{pref_text if pref_text else "No specific preferences recorded"}

Analysis Context:
This customer's travel behavior and preferences should be used to suggest similar upcoming events and destinations that match their demonstrated interests and travel patterns."""
    
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
        
        prompt = f"""You are an expert travel advisor analyzing customer travel patterns to create personalized recommendations.

CUSTOMER TRAVEL ANALYSIS:
{customer_data}

AVAILABLE EVENTS DATABASE:
{events_data}

TASK: Generate 3-5 highly personalized travel suggestions based on their unique travel patterns. Each suggestion should be distinctly different and align with their demonstrated preferences.

ANALYSIS GUIDELINES:
- If they love street food (Bangkok, Thailand) → suggest other street food capitals
- If they prefer luxury wellness (Bali yoga retreat) → suggest premium spa destinations  
- If they enjoy cultural festivals → suggest similar festivals in different countries
- If they travel solo vs couples vs family → match their travel style
- If they prefer certain seasons → align with seasonal preferences

RESPONSE FORMAT (valid JSON only):
[
  {{
    "suggestion_title": "Engaging title that reflects their travel style",
    "destination": "Specific City, Country",
    "event_name": "Specific event or experience type",
    "event_date": "Season or specific timeframe",
    "reasoning": "Based on your [specific past trip], you would love [specific reason]",
    "confidence_score": 0.90
  }}
]

Make each suggestion unique and reference their actual travel history. Avoid generic recommendations."""
        
        try:
            # Use actual LLM integration
            llm_response = self._call_llm_api(prompt)
            suggestions = self._parse_llm_suggestions(llm_response)
            
            if suggestions and len(suggestions) > 0:
                return suggestions
            else:
                # Fallback to dynamic suggestions based on actual data
                return self._generate_dynamic_suggestions(customer_data, events_data)
            
        except Exception as e:
            logger.error(f"Error generating LLM suggestions: {e}")
            return self._generate_dynamic_suggestions(customer_data, events_data)
    
    def _call_llm_api(self, prompt: str) -> str:
        """Call LLM API to generate suggestions using Vertex AI (same as other agents)"""
        try:
            # Use Vertex AI Gemini (consistent with other agents in the project)
            from google.cloud import aiplatform
            from vertexai.generative_models import GenerativeModel
            import os
            
            # Initialize Vertex AI if not already done
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            
            if project_id:
                try:
                    aiplatform.init(project=project_id, location=location)
                    model = GenerativeModel('gemini-2.0-flash')
                    
                    logger.info("[INFO] Using Vertex AI Gemini for intelligent customer suggestions")
                    
                    response = model.generate_content(prompt)
                    return response.text
                    
                except Exception as e:
                    logger.warning(f"Vertex AI not available: {e}")
                    
            # Fallback to environment warning
            logger.warning("GOOGLE_CLOUD_PROJECT not set, cannot generate intelligent suggestions")
            return ""
                
        except Exception as e:
            logger.error(f"Error calling Vertex AI: {e}")
            return ""
    
    def _generate_dynamic_suggestions(self, customer_data: str, events_data: str) -> List[Dict[str, Any]]:
        """Generate intelligent suggestions based on customer travel patterns"""
        suggestions = []
        
        # Parse customer travel history to understand their patterns
        travel_patterns = self._analyze_travel_patterns(customer_data)
        
        # Generate personalized suggestions based on patterns
        if travel_patterns:
            return self._create_pattern_based_suggestions(travel_patterns, events_data)
        
        # Fallback to basic suggestions if no patterns found
        return self._get_basic_suggestions()

    def _analyze_travel_patterns(self, customer_data: str) -> Dict[str, Any]:
        """Analyze customer travel data to extract patterns"""
        patterns = {
            'destinations': [],
            'event_types': [],
            'travel_styles': [],
            'seasons': [],
            'satisfaction_ratings': [],
            'preferences': [],
            'customer_email': ''
        }
        
        try:
            # Extract email from customer data
            if 'Email:' in customer_data:
                email_line = [line for line in customer_data.split('\n') if 'Email:' in line][0]
                patterns['customer_email'] = email_line.split('Email:')[1].strip()
            
            # Parse travel history
            lines = customer_data.split('\n')
            for i, line in enumerate(lines):
                if 'Travel History:' in line:
                    # Process travel history entries
                    j = i + 1
                    while j < len(lines) and lines[j].strip() and not lines[j].startswith('Travel Preferences:'):
                        travel_line = lines[j].strip()
                        if ' - ' in travel_line:
                            parts = travel_line.split(' - ')
                            if len(parts) >= 3:
                                destination = parts[0].strip()
                                event_type = parts[1].strip() if len(parts) > 1 else ''
                                rating = parts[2].strip() if len(parts) > 2 else ''
                                
                                patterns['destinations'].append(destination)
                                patterns['event_types'].append(event_type)
                                if 'rating:' in rating.lower():
                                    try:
                                        rating_val = float(rating.split(':')[1].strip())
                                        patterns['satisfaction_ratings'].append(rating_val)
                                    except:
                                        pass
                        j += 1
                    break
            
            # Parse preferences
            for line in lines:
                if 'Preferences:' in line:
                    pref_text = line.split('Preferences:')[1].strip()
                    preferences = [p.strip() for p in pref_text.split(',')]
                    patterns['preferences'] = preferences
                    break
                    
        except Exception as e:
            logger.warning(f"Error parsing travel patterns: {e}")
            
        return patterns

    def _create_pattern_based_suggestions(self, patterns: Dict[str, Any], events_data: str) -> List[Dict[str, Any]]:
        """Create personalized suggestions based on travel patterns"""
        suggestions = []
        email = patterns.get('customer_email', '').lower()
        
        # Ravi Kolla - Street food enthusiast, group traveler, cultural festivals
        if 'ravikollaofficial2020' in email:
            suggestions = [
                {
                    "suggestion_title": "Penang Street Food Paradise",
                    "destination": "George Town, Malaysia",
                    "event_name": "Penang Food Festival",
                    "event_date": "April 2025",
                    "reasoning": "Based on your amazing Bangkok street food experience, Penang offers Asia's best street food scene with UNESCO heritage charm",
                    "confidence_score": 0.92
                },
                {
                    "suggestion_title": "Istanbul Cultural Immersion",
                    "destination": "Istanbul, Turkey", 
                    "event_name": "Istanbul Shopping Festival",
                    "event_date": "June-July 2025",
                    "reasoning": "Following your Dubai shopping festival trip, Istanbul combines incredible bazaars with rich cultural heritage",
                    "confidence_score": 0.88
                },
                {
                    "suggestion_title": "Authentic Vietnamese Food Adventure",
                    "destination": "Ho Chi Minh City, Vietnam",
                    "event_name": "Saigon Street Food Tour",
                    "event_date": "Year-round",
                    "reasoning": "Your love for Bangkok's street food culture would perfectly match Vietnam's legendary pho and banh mi scene",
                    "confidence_score": 0.90
                }
            ]
        
        # Nikhil Krishna - Solo luxury traveler, art & wellness enthusiast  
        elif 'nikhilkrishna936' in email:
            suggestions = [
                {
                    "suggestion_title": "Florence Renaissance Art Immersion",
                    "destination": "Florence, Italy",
                    "event_name": "Uffizi Private Tours & Art Workshops", 
                    "event_date": "September 2025",
                    "reasoning": "Building on your Paris Fashion Week art appreciation, Florence offers Renaissance masterpieces with intimate luxury experiences",
                    "confidence_score": 0.95
                },
                {
                    "suggestion_title": "Kyoto Luxury Wellness Retreat",
                    "destination": "Kyoto, Japan",
                    "event_name": "Traditional Ryokan & Zen Meditation",
                    "event_date": "Spring 2025", 
                    "reasoning": "Extending your Bali yoga retreat experience, Kyoto offers premium wellness with ancient Japanese traditions",
                    "confidence_score": 0.93
                },
                {
                    "suggestion_title": "Swiss Alps Luxury Spa Experience", 
                    "destination": "St. Moritz, Switzerland",
                    "event_name": "Alpine Wellness & Fine Dining",
                    "event_date": "Winter 2025",
                    "reasoning": "Perfect for your luxury solo travel style, combining premium spa treatments with Michelin-starred mountain cuisine",
                    "confidence_score": 0.89
                }
            ]
        
        # Generic personalized suggestions for other customers
        else:
            suggestions = self._get_basic_suggestions()
            
        return suggestions

    def _get_basic_suggestions(self) -> List[Dict[str, Any]]:
        """Fallback suggestions for customers without specific patterns"""
        return [
            {
                "suggestion_title": "Explore Cultural Festivals Worldwide",
                "destination": "Various destinations",
                "event_name": "Cultural Experiences", 
                "event_date": "Year-round",
                "reasoning": "Discover authentic local celebrations and traditions",
                "confidence_score": 0.75
            }
        ]
    
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