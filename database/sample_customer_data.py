#!/usr/bin/env python3
"""
Sample customer data insertion script for testing the customer profile system
"""

import sys
import os
import json
from datetime import date, timedelta

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_db, engine
from models.customer_profile import (
    CustomerProfile, CustomerTravelHistory, 
    CustomerPreference, EventCalendar, Base
)
from sqlalchemy.orm import Session

def create_sample_data():
    """Insert sample customer profile data for testing"""
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Get database session
    db = Session(engine)
    
    try:
        # Sample customers
        customers = [
            {
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe'
            },
            {
                'email': 'jane.smith@example.com', 
                'first_name': 'Jane',
                'last_name': 'Smith'
            },
            {
                'email': 'henry.thomas596@yahoo.com',
                'first_name': 'Henry',
                'last_name': 'Thomas'
            }
        ]
        
        for customer_data in customers:
            # Create customer profile if not exists
            existing = db.query(CustomerProfile).filter(
                CustomerProfile.email == customer_data['email']
            ).first()
            
            if not existing:
                customer = CustomerProfile(**customer_data)
                db.add(customer)
                print(f"Created customer: {customer_data['email']}")
        
        db.commit()
        
        # Sample travel history
        travel_histories = [
            {
                'customer_email': 'john.doe@example.com',
                'destination': 'Bangalore, India',
                'country': 'India',
                'city': 'Bangalore',
                'event_name': 'Diwali Festival',
                'event_type': 'festival',
                'travel_date_start': date(2023, 11, 12),
                'travel_date_end': date(2023, 11, 15),
                'season': 'post-monsoon',
                'travel_style': 'family',
                'budget_range': 'mid-range',
                'satisfaction_rating': 5,
                'notes': 'Loved the festival atmosphere and cultural experience'
            },
            {
                'customer_email': 'john.doe@example.com',
                'destination': 'Munich, Germany',
                'country': 'Germany',
                'city': 'Munich',
                'event_name': 'Oktoberfest',
                'event_type': 'festival',
                'travel_date_start': date(2023, 9, 20),
                'travel_date_end': date(2023, 9, 25),
                'season': 'autumn',
                'travel_style': 'group',
                'budget_range': 'luxury',
                'satisfaction_rating': 4,
                'notes': 'Great beer, food, and atmosphere with friends'
            },
            {
                'customer_email': 'jane.smith@example.com',
                'destination': 'Rajasthan, India',
                'country': 'India',
                'city': 'Jaipur',
                'event_name': 'Holi Festival',
                'event_type': 'festival',
                'travel_date_start': date(2023, 3, 8),
                'travel_date_end': date(2023, 3, 10),
                'season': 'spring',
                'travel_style': 'couple',
                'budget_range': 'mid-range',
                'satisfaction_rating': 5,
                'notes': 'Amazing colors and cultural immersion in Rajasthan'
            },
            {
                'customer_email': 'henry.thomas596@yahoo.com',
                'destination': 'Tokyo, Japan',
                'country': 'Japan',
                'city': 'Tokyo',
                'event_name': 'Cherry Blossom Festival',
                'event_type': 'festival',
                'travel_date_start': date(2023, 4, 5),
                'travel_date_end': date(2023, 4, 12),
                'season': 'spring',
                'travel_style': 'solo',
                'budget_range': 'luxury',
                'satisfaction_rating': 5,
                'notes': 'Perfect timing for sakura season, incredible experience'
            },
            {
                'customer_email': 'henry.thomas596@yahoo.com',
                'destination': 'Goa, India',
                'country': 'India',
                'city': 'Panaji',
                'event_name': 'Christmas and New Year',
                'event_type': 'festival',
                'travel_date_start': date(2022, 12, 23),
                'travel_date_end': date(2023, 1, 2),
                'season': 'winter',
                'travel_style': 'family',
                'budget_range': 'mid-range',
                'satisfaction_rating': 4,
                'notes': 'Great beaches, food, and celebration atmosphere'
            }
        ]
        
        for history_data in travel_histories:
            existing = db.query(CustomerTravelHistory).filter(
                CustomerTravelHistory.customer_email == history_data['customer_email'],
                CustomerTravelHistory.destination == history_data['destination'],
                CustomerTravelHistory.travel_date_start == history_data['travel_date_start']
            ).first()
            
            if not existing:
                history = CustomerTravelHistory(**history_data)
                db.add(history)
                print(f"Added travel history: {history_data['customer_email']} -> {history_data['destination']}")
        
        db.commit()
        
        # Sample preferences
        preferences = [
            {
                'customer_email': 'john.doe@example.com',
                'preference_type': 'accommodation',
                'preference_value': 'boutique_hotels',
                'weight': 3
            },
            {
                'customer_email': 'john.doe@example.com',
                'preference_type': 'activity',
                'preference_value': 'cultural_festivals',
                'weight': 5
            },
            {
                'customer_email': 'jane.smith@example.com',
                'preference_type': 'travel_style',
                'preference_value': 'romantic',
                'weight': 4
            },
            {
                'customer_email': 'henry.thomas596@yahoo.com',
                'preference_type': 'activity',
                'preference_value': 'photography',
                'weight': 5
            },
            {
                'customer_email': 'henry.thomas596@yahoo.com',
                'preference_type': 'season',
                'preference_value': 'spring_blooms',
                'weight': 4
            }
        ]
        
        for pref_data in preferences:
            existing = db.query(CustomerPreference).filter(
                CustomerPreference.customer_email == pref_data['customer_email'],
                CustomerPreference.preference_type == pref_data['preference_type'],
                CustomerPreference.preference_value == pref_data['preference_value']
            ).first()
            
            if not existing:
                preference = CustomerPreference(**pref_data)
                db.add(preference)
                print(f"Added preference: {pref_data['customer_email']} -> {pref_data['preference_value']}")
        
        db.commit()
        
        # Sample upcoming events
        today = date.today()
        upcoming_events = [
            {
                'event_name': 'Dussehra Festival',
                'event_type': 'festival',
                'destination': 'Mysore, India',
                'country': 'India',
                'city': 'Mysore',
                'event_date_start': today + timedelta(days=30),
                'event_date_end': today + timedelta(days=30),
                'description': 'Grand Dussehra celebration in the royal city of Mysore with processions and cultural programs',
                'season': 'post-monsoon',
                'similar_events': json.dumps(['Diwali', 'Navratri', 'Durga Puja'])
            },
            {
                'event_name': 'Christmas Markets',
                'event_type': 'festival',
                'destination': 'Vienna, Austria',
                'country': 'Austria',
                'city': 'Vienna',
                'event_date_start': today + timedelta(days=60),
                'event_date_end': today + timedelta(days=84),
                'description': 'Traditional Christmas markets with mulled wine, crafts, and holiday atmosphere',
                'season': 'winter',
                'similar_events': json.dumps(['Oktoberfest', 'Winter festivals', 'Christmas celebrations'])
            },
            {
                'event_name': 'Cherry Blossom Festival',
                'event_type': 'festival', 
                'destination': 'Kyoto, Japan',
                'country': 'Japan',
                'city': 'Kyoto',
                'event_date_start': today + timedelta(days=180),
                'event_date_end': today + timedelta(days=194),
                'description': 'Beautiful cherry blossom season in historic Kyoto temples and gardens',
                'season': 'spring',
                'similar_events': json.dumps(['Spring festivals', 'Nature festivals', 'Cultural events'])
            },
            {
                'event_name': 'Holi Festival',
                'event_type': 'festival',
                'destination': 'Mathura, India', 
                'country': 'India',
                'city': 'Mathura',
                'event_date_start': today + timedelta(days=150),
                'event_date_end': today + timedelta(days=150),
                'description': 'The original Holi celebration in Krishna\'s birthplace with vibrant colors',
                'season': 'spring',
                'similar_events': json.dumps(['Diwali', 'Dussehra', 'Color festivals'])
            }
        ]
        
        for event_data in upcoming_events:
            existing = db.query(EventCalendar).filter(
                EventCalendar.event_name == event_data['event_name'],
                EventCalendar.destination == event_data['destination'],
                EventCalendar.event_date_start == event_data['event_date_start']
            ).first()
            
            if not existing:
                event = EventCalendar(**event_data)
                db.add(event)
                print(f"Added upcoming event: {event_data['event_name']} in {event_data['destination']}")
        
        db.commit()
        
        print("\n✅ Sample customer profile data created successfully!")
        print("\nTest emails to try:")
        print("• john.doe@example.com (Diwali + Oktoberfest history)")
        print("• jane.smith@example.com (Holi festival history)")
        print("• henry.thomas596@yahoo.com (Cherry Blossom + Goa history)")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()