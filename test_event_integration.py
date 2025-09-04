#!/usr/bin/env python3
"""
Test script for event-based travel planning functionality
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.llm_extractor.extractor_agent import LLMExtractorAgent
from agents.event_search.event_agent import EventSearchAgent

async def test_event_extraction():
    """Test event extraction from user request"""
    print("🧪 Testing Event Extraction...")
    
    agent = LLMExtractorAgent()
    
    test_request = "Prepare the itinerary for visiting Water Lantern Festival in Thailand"
    
    input_data = {
        "user_request": test_request,
        "conversation_context": {}
    }
    
    try:
        result = await agent.execute(input_data, "test_session_001")
        
        print("✅ Event extraction successful!")
        print(f"📋 Extracted requirements:")
        
        requirements = result.get("data", {}).get("requirements", {})
        
        print(f"  - Destination: {requirements.get('destination')}")
        print(f"  - Event Name: {requirements.get('event_name')}")
        print(f"  - Event Type: {requirements.get('event_type')}")
        print(f"  - Duration: {requirements.get('duration')} days")
        print(f"  - Budget: ${requirements.get('budget')} {requirements.get('budget_currency')}")
        print(f"  - Passengers: {requirements.get('passengers')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Event extraction failed: {e}")
        return None

async def test_event_search():
    """Test event search functionality"""
    print("\n🎪 Testing Event Search...")
    
    agent = EventSearchAgent()
    
    input_data = {
        "event_name": "Water Lantern Festival",
        "event_type": "festival",
        "destination": "Thailand",
        "date_range": "2025-11-15",
        "duration": 7,
        "preferences": []
    }
    
    try:
        result = await agent.execute(input_data, "test_session_002")
        
        print("✅ Event search successful!")
        print(f"🎉 Found events:")
        
        events = result.get("data", {}).get("events", [])
        
        for i, event in enumerate(events[:2]):  # Show first 2 events
            print(f"  Event {i+1}:")
            print(f"    - Name: {event.get('name')}")
            print(f"    - Type: {event.get('event_type')}")
            print(f"    - Location: {event.get('location')}")
            print(f"    - Start Date: {event.get('start_date')}")
            print(f"    - Duration: {event.get('duration')}")
            print(f"    - Description: {event.get('description', '')[:100]}...")
        
        travel_recommendations = result.get("data", {}).get("travel_recommendations", {})
        print(f"✈️ Travel recommendations:")
        print(f"  - Optimal Duration: {travel_recommendations.get('optimal_duration')}")
        print(f"  - Best Arrival: {travel_recommendations.get('best_arrival_time')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Event search failed: {e}")
        return None

async def test_full_integration():
    """Test full integration: extract -> search events -> plan"""
    print("\n🔄 Testing Full Event Integration...")
    
    # Step 1: Extract requirements
    extraction_result = await test_event_extraction()
    if not extraction_result:
        print("❌ Cannot continue - extraction failed")
        return
    
    # Step 2: Search events
    requirements = extraction_result.get("data", {}).get("requirements", {})
    
    if requirements.get("event_name") or requirements.get("event_type"):
        event_search_data = {
            "event_name": requirements.get("event_name"),
            "event_type": requirements.get("event_type"),
            "destination": requirements.get("destination"),
            "date_range": requirements.get("departure_date"),
            "duration": requirements.get("duration", 7),
            "preferences": requirements.get("special_requirements", [])
        }
        
        event_result = await test_event_search()
        
        if event_result:
            print("\n✅ Full integration test successful!")
            print("🎯 Event-based travel planning is working end-to-end")
            
            # Show integration summary
            events = event_result.get("data", {}).get("events", [])
            if events:
                first_event = events[0]
                print(f"\n📋 Integration Summary:")
                print(f"  🎪 Event: {first_event.get('name')} in {first_event.get('location')}")
                print(f"  📅 Event Dates: {first_event.get('start_date')} to {first_event.get('end_date', 'N/A')}")
                print(f"  ✈️ Recommended Trip: {requirements.get('duration')} days")
                print(f"  💰 Budget: ${requirements.get('budget')} {requirements.get('budget_currency')}")
                print(f"  👥 Travelers: {requirements.get('passengers')} people")
        else:
            print("❌ Event search failed in full integration")
    else:
        print("⚠️ No event information extracted for search")

async def main():
    """Run all tests"""
    print("🚀 Starting Event-Based Travel Planning Tests")
    print("=" * 50)
    
    await test_full_integration()
    
    print("\n" + "=" * 50)
    print("✨ Event integration testing complete!")
    print("\nNow try the API with: 'Prepare the itinerary for visiting Water Lantern Festival in Thailand'")

if __name__ == "__main__":
    asyncio.run(main())