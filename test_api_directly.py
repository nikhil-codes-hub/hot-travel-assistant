#!/usr/bin/env python3
"""
Test the API directly to get the event-enhanced response
"""

import requests
import json
from datetime import datetime

def test_event_api():
    """Test the event-enhanced API directly"""
    
    print("🎯 TESTING WATER LANTERN FESTIVAL API DIRECTLY")
    print("=" * 60)
    
    # API endpoint (adjust port if needed)
    url = "http://localhost:8000/travel/search"
    
    # Your exact request
    payload = {
        "user_request": "Prepare an itinerary for Water Lantern festival in Thailand",
        "session_id": f"test_water_lantern_{int(datetime.now().timestamp())}",
        "customer_id": "test_customer",
        "nationality": "US"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"📡 Making API call to: {url}")
        print(f"📝 Payload: {json.dumps(payload, indent=2)}")
        print()
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ API SUCCESS!")
            print()
            
            # Check if we got event-enhanced response
            response_data = data.get('data', {})
            
            # Check requirements
            requirements = response_data.get('requirements', {})
            if hasattr(requirements, 'get') and 'data' in requirements:
                req_data = requirements['data'].get('requirements', {})
                event_name = req_data.get('event_name')
                event_type = req_data.get('event_type')
                
                print(f"🎪 EVENT EXTRACTION:")
                print(f"  Event Name: {event_name or '❌ MISSING'}")
                print(f"  Event Type: {event_type or '❌ MISSING'}")
                print()
            
            # Check itinerary
            itinerary = response_data.get('itinerary', {})
            if hasattr(itinerary, 'get') and 'data' in itinerary:
                itinerary_data = itinerary['data'].get('itinerary', {})
                title = itinerary_data.get('title', 'No title')
                rationale = itinerary_data.get('rationale', 'No rationale')
                highlights = itinerary_data.get('highlights', [])
                
                print(f"📋 ITINERARY RESPONSE:")
                print(f"  Title: {title}")
                print(f"  ✅ Has 'Lantern': {'Lantern' in title}")
                print(f"  ✅ Has 'EVENT FOCUS': {'EVENT FOCUS' in rationale}")
                print()
                print(f"  Highlights:")
                for i, highlight in enumerate(highlights[:3], 1):
                    print(f"    {i}. {highlight}")
                print()
                print(f"  Rationale: {rationale[:200]}...")
                print()
                
                # Check if we got the event-enhanced response
                has_event_title = 'Lantern' in title
                has_event_focus = 'EVENT FOCUS' in rationale
                has_event_highlights = any('Lantern' in str(h) for h in highlights)
                
                if has_event_title and has_event_focus:
                    print("🎉 SUCCESS: Event-enhanced response received!")
                    print("✅ Water Lantern Festival is properly integrated")
                else:
                    print("❌ ISSUE: Still getting generic response")
                    print("🔍 Debugging needed:")
                    print(f"  - Event in title: {has_event_title}")
                    print(f"  - Event focus in rationale: {has_event_focus}")
                    print(f"  - Event in highlights: {has_event_highlights}")
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API Call Failed: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Make sure your API server is running on port 8000")
        print("2. Try: uvicorn api.main:app --reload --port 8000")
        print("3. Check if you're calling the correct endpoint")

if __name__ == "__main__":
    test_event_api()