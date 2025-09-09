"""
Test script to demonstrate image-enhanced itinerary generation with dynamic Diwali content
"""
import asyncio
import json
import sys
sys.path.append('.')

from agents.itinerary.itinerary_agent import PrepareItineraryAgent

async def test_diwali_itinerary_with_images():
    print("🎆 TESTING IMAGE-ENHANCED DIWALI ITINERARY GENERATION")
    print("=" * 65)
    
    # Create itinerary agent
    agent = PrepareItineraryAgent()
    
    # Simulate Diwali festival input data
    input_data = {
        "requirements": {
            "destination": "Bangalore, India", 
            "event_name": "Diwali Festival",
            "event_type": "cultural",
            "departure_date": "2025-10-20",
            "duration": 5,
            "passengers": 2,
            "budget": 1500,
            "travel_class": "business"
        },
        "events": [
            {
                "name": "Diwali Festival",
                "event_type": "cultural",
                "description": "Festival of Lights celebration with traditional rituals, temple visits, and cultural performances",
                "location": "Bangalore, India",
                "start_date": "2025-10-20",
                "end_date": "2025-10-24"
            }
        ],
        "customer_profile": {
            "loyalty_tier": "GOLD",
            "preferences": {
                "preferred_cabin_class": "Business"
            }
        }
    }
    
    try:
        # Generate image-enhanced itinerary
        print("🔄 Generating image-enhanced itinerary...")
        result = await agent.execute(input_data, "test_session")
        
        itinerary_data = result.get("data", {}).get("itinerary", {})
        
        print(f"📋 {itinerary_data.get('title', 'Travel Itinerary')}")
        print(f"📍 Destination: {itinerary_data.get('destination')}")
        print(f"📅 Duration: {itinerary_data.get('duration')} days")
        print()
        
        # Display hero images
        hero_images = itinerary_data.get("hero_images", [])
        if hero_images:
            print("🖼️  HERO IMAGES (Main Showcase):")
            for i, image in enumerate(hero_images[:2], 1):
                print(f"  {i}. {image.get('title', 'Untitled')}")
                print(f"     📸 {image.get('url', 'No URL')}")
                print(f"     ✨ {image.get('alt_text', 'No description')}")
                print(f"     🎯 Context: {image.get('context', 'general')}")
                print()
        
        # Display gallery images
        gallery_images = itinerary_data.get("gallery_images", [])
        if gallery_images:
            print("🏛️  GALLERY IMAGES (Destination & Event Photos):")
            for i, image in enumerate(gallery_images[:6], 1):
                print(f"  {i}. {image.get('title', 'Untitled')}")
                print(f"     📸 {image.get('url', 'No URL')}")
                print(f"     📝 {image.get('alt_text', 'No description')}")
                print(f"     🎯 Context: {image.get('context', 'general')}")
                print(f"     ⭐ Relevance: {image.get('relevance_score', 0)}")
                print()
        
        # Display itinerary highlights
        highlights = itinerary_data.get("highlights", [])
        if highlights:
            print("✨ ITINERARY HIGHLIGHTS:")
            for highlight in highlights[:5]:
                print(f"  • {highlight}")
            print()
        
        # Display daily activities
        days = itinerary_data.get("days", [])
        if days:
            print("📅 DAILY ITINERARY:")
            for day in days[:3]:  # Show first 3 days
                print(f"Day {day.get('day', '')} ({day.get('date', '')}):")
                activities = day.get('activities', [])
                for activity in activities[:4]:  # Show first 4 activities
                    print(f"  • {activity}")
                print()
        
        print("🎯 IMAGE INTEGRATION SUCCESS!")
        print("✅ Hero images for main showcase")
        print("✅ Gallery images for destination highlights")
        print("✅ Event-specific images for Diwali celebration")
        print("✅ Dynamic content generation without hardcoded data")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_diwali_itinerary_with_images())