#!/usr/bin/env python3
"""
Show the complete dynamic event-based API response structure
"""

import json

# This demonstrates the complete API response structure you'll get
# when calling POST /travel/search with "Prepare an itinerary for Lantern event in Thailand"

def show_dynamic_api_response():
    print("🎯 DYNAMIC EVENT-BASED API RESPONSE STRUCTURE")
    print("=" * 60)
    print()
    print("📡 API Call:")
    print('POST /travel/search')
    print('{"user_request": "Prepare an itinerary for Lantern event in Thailand"}')
    print()
    print("📋 Dynamic Response Structure:")
    print()
    
    # This is the actual response structure your API generates
    response_structure = {
        "session_id": "auto-generated-uuid",
        "status": "completed",
        "data": {
            "requirements": {
                "agent": "LLMExtractorAgent",
                "data": {
                    "requirements": {
                        "destination": "Thailand",
                        "event_name": "DYNAMICALLY EXTRACTED EVENT NAME",
                        "event_type": "DYNAMICALLY EXTRACTED EVENT TYPE", 
                        "departure_date": "2025-10-04",
                        "duration": 7,
                        "budget": 2500.0,
                        "budget_currency": "USD",
                        "passengers": 2,
                        "travel_class": "economy"
                    },
                    "confidence_score": 0.8,
                    "planning_context": {
                        "requires_comprehensive_planning": True,
                        "defaults_applied": True,
                        "destination_specificity": "extracted"
                    }
                }
            },
            "event_details": {
                "agent": "EventSearchAgent", 
                "data": {
                    "events": [
                        {
                            "event_id": "DYNAMIC_EVENT_ID",
                            "name": "DYNAMIC EVENT NAME (e.g., Water Lantern Festival)",
                            "event_type": "festival",
                            "description": "DYNAMIC EVENT DESCRIPTION with cultural context",
                            "location": "DYNAMIC LOCATION (e.g., Chiang Mai, Thailand)",
                            "start_date": "DYNAMIC DATE based on event schedule",
                            "duration": "DYNAMIC DURATION (e.g., 1 evening, 3 days)",
                            "cultural_significance": "DYNAMIC cultural context and meaning",
                            "what_to_bring": ["DYNAMIC", "items", "specific", "to", "event"],
                            "weather_considerations": "DYNAMIC weather advice",
                            "ticket_info": {
                                "required": True,
                                "advance_booking": "DYNAMIC booking timeline",
                                "price_range": "DYNAMIC price range"
                            }
                        }
                    ],
                    "travel_recommendations": {
                        "optimal_duration": "DYNAMIC duration recommendation",
                        "best_arrival_time": "DYNAMIC arrival timing", 
                        "accommodation_booking": "DYNAMIC booking advice",
                        "travel_tips": ["DYNAMIC", "event-specific", "travel", "tips"]
                    },
                    "destination_context": {
                        "country": "Thailand",
                        "best_airports": ["DYNAMIC nearest airports"],
                        "local_transportation": "DYNAMIC transport advice",
                        "local_customs": "DYNAMIC cultural etiquette"
                    }
                }
            },
            "destination_suggestions": {
                "agent": "DestinationDiscoveryAgent",
                "data": {
                    "suggestions": ["DYNAMIC destination suggestions if needed"]
                }
            },
            "flight_offers": ["DYNAMIC flight search results from Amadeus API"],
            "hotel_offers": ["DYNAMIC hotel search results from Amadeus API"],
            "itinerary": {
                "agent": "PrepareItineraryAgent", 
                "data": {
                    "days": [
                        {
                            "day": 1,
                            "activities": ["DYNAMIC activities"],
                            "event_focus": "Pre-event preparation"
                        },
                        {
                            "day": 4,
                            "activities": [
                                "🏮 MAIN EVENT: [DYNAMIC EVENT NAME]",
                                "DYNAMIC event schedule",
                                "DYNAMIC event activities"
                            ],
                            "event_focus": "MAIN EVENT DAY"
                        }
                    ],
                    "event_integration": "DYNAMIC event-focused planning",
                    "cultural_notes": "DYNAMIC cultural context for the event"
                }
            }
        },
        "timestamp": "AUTO-GENERATED"
    }
    
    print(json.dumps(response_structure, indent=2))
    print()
    print("🎉 KEY DYNAMIC FEATURES:")
    print("✅ Event name/type extracted from natural language")
    print("✅ Event details searched and integrated into travel plan")
    print("✅ Travel requirements enhanced based on event timing")
    print("✅ Itinerary built around event schedule")
    print("✅ Cultural context and practical tips provided")
    print("✅ Flights/hotels searched with event location in mind")
    print("✅ All requirements and dates optimized for event attendance")
    print()
    print("🔗 INTEGRATION FLOW:")
    print("1. Extract event info from user request")
    print("2. Search for detailed event information")
    print("3. Enhance travel requirements with event context")
    print("4. Search flights/hotels near event location")
    print("5. Generate event-focused itinerary")
    print("6. Add cultural context and practical tips")
    print()
    print("🚀 To get this dynamic response:")
    print("   Start your API server: uvicorn api.main:app --reload")
    print('   POST /travel/search with your event query')

if __name__ == "__main__":
    show_dynamic_api_response()