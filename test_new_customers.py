#!/usr/bin/env python3
"""
Test script to verify the new customer profiles work correctly
"""

import requests
import json

def test_customer_profile_api():
    """Test customer profile API with new email addresses"""
    
    base_url = "http://localhost:8000"
    test_emails = [
        "ravikollaofficial2020@gmail.com",
        "nikhilkrishna936@gmail.com"
    ]
    
    print("🧪 Testing new customer profiles...")
    
    for email in test_emails:
        print(f"\n📧 Testing: {email}")
        
        try:
            # Test customer profile endpoint
            response = requests.get(f"{base_url}/customer/profile", params={"email": email})
            
            if response.status_code == 200:
                profile_data = response.json()
                print(f"✅ Profile loaded successfully!")
                print(f"   Name: {profile_data.get('customer_name', 'N/A')}")
                print(f"   Travel History: {profile_data.get('travel_history_count', 0)} trips")
                print(f"   Preferences: {len(profile_data.get('preferences', []))} preferences")
                
                # Show travel history details
                if profile_data.get('travel_history'):
                    print("   Recent trips:")
                    for trip in profile_data['travel_history'][:3]:  # Show first 3 trips
                        print(f"     • {trip.get('destination')} ({trip.get('travel_date_start')}) - {trip.get('satisfaction_rating', 'N/A')}⭐")
                
                # Show preferences
                if profile_data.get('preferences'):
                    print("   Top preferences:")
                    for pref in profile_data['preferences'][:3]:  # Show first 3 preferences
                        print(f"     • {pref.get('preference_type')}: {pref.get('preference_value')} (weight: {pref.get('weight', 'N/A')})")
                        
            else:
                print(f"❌ Failed to load profile: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to API server at {base_url}")
            print("   Make sure the API server is running on port 8000")
            break
        except Exception as e:
            print(f"❌ Error testing {email}: {e}")

def summarize_profiles():
    """Summarize the customer profiles we created"""
    
    print("\n📊 Customer Profile Summary:")
    print("="*50)
    
    print("\n🏠 Ravi Kolla (ravikollaofficial2020@gmail.com)")
    print("   • Travel Style: Group adventures, cultural festivals")
    print("   • Preferences: Street food tours, boutique hotels, value for money")
    print("   • Recent Trips:")
    print("     - Bangkok, Thailand (Songkran Festival) - 5⭐")
    print("     - Dubai, UAE (Shopping Festival) - 4⭐") 
    print("     - Kerala, India (Monsoon Season) - 5⭐")
    
    print("\n🎯 Nikhil Krishna (nikhilkrishna936@gmail.com)")
    print("   • Travel Style: Solo exploration, luxury experiences")
    print("   • Preferences: Art museums, fine dining, wellness retreats")
    print("   • Recent Trips:")
    print("     - Paris, France (Fashion Week) - 5⭐")
    print("     - Mysore, India (Dasara Festival) - 5⭐")
    print("     - Singapore (Chinese New Year) - 4⭐")
    print("     - Bali, Indonesia (Yoga Retreat) - 5⭐")

if __name__ == "__main__":
    summarize_profiles()
    test_customer_profile_api()
    print("\n🎉 New customer profiles are ready for testing in the UI!")
    print("💡 Try entering the new email addresses in the frontend to see their rich travel histories!")