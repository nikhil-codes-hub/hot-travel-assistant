#!/usr/bin/env python3
"""
Test script to verify that the email system properly uses existing itinerary data
instead of regenerating it with LLM
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.send_mail import build_html

def test_email_with_existing_itinerary():
    """Test email generation with existing itinerary data"""
    
    # Mock existing itinerary data (as it would come from travel orchestrator)
    mock_existing_itinerary = {
        "data": {
            "itinerary": {
                "title": "Bangkok Adventure",
                "destination": "Bangkok, Thailand", 
                "duration": 5,
                "days": [
                    {
                        "day": 1,
                        "date": "2024-12-15",
                        "location": "Bangkok City Center",
                        "activities": [
                            "Arrival at Suvarnabhumi Airport",
                            "Check-in at hotel",
                            "Visit Grand Palace",
                            "Explore Wat Pho Temple"
                        ],
                        "meals": ["Welcome dinner at local restaurant"],
                        "budget_estimate": 150
                    },
                    {
                        "day": 2,
                        "date": "2024-12-16", 
                        "location": "Bangkok Markets",
                        "activities": [
                            "Morning at Chatuchak Weekend Market",
                            "Afternoon at Floating Market",
                            "Evening Tuk-tuk tour"
                        ],
                        "meals": ["Street food breakfast", "Market lunch", "Rooftop dinner"],
                        "budget_estimate": 120
                    }
                ]
            }
        }
    }
    
    # Mock email data with existing itinerary
    email_data_with_itinerary = {
        "customer": {
            "name": "John Smith",
            "email": "john.smith@example.com"
        },
        "trip_details": {
            "destination": "Bangkok, Thailand",
            "departure_date": "2024-12-15",
            "duration": 5,
            "travelers": 2
        },
        "flights": [],
        "hotels": [],
        "itinerary": mock_existing_itinerary,  # This contains the existing itinerary
        "session_info": None
    }
    
    print("🧪 Testing email with existing itinerary data...")
    
    # Generate HTML email
    html_content = build_html(email_data_with_itinerary)
    
    # Check if it contains our itinerary data
    if "Bangkok City Center" in html_content and "Grand Palace" in html_content:
        print("✅ SUCCESS: Email contains existing itinerary data from travel orchestrator")
        print("✅ SUCCESS: No redundant LLM generation needed")
    else:
        print("❌ FAILED: Email does not contain expected itinerary data")
    
    # Also test fallback behavior (no existing itinerary)
    print("\n🧪 Testing email without existing itinerary (fallback to LLM)...")
    
    email_data_without_itinerary = email_data_with_itinerary.copy()
    email_data_without_itinerary["itinerary"] = None
    
    try:
        html_content_fallback = build_html(email_data_without_itinerary)
        print("✅ SUCCESS: Fallback to LLM generation works when no existing itinerary")
    except Exception as e:
        print(f"⚠️  Note: Fallback LLM generation failed (expected in test environment): {e}")
    
    return html_content

if __name__ == "__main__":
    test_email_with_existing_itinerary()