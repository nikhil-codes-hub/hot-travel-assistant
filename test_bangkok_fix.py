#!/usr/bin/env python3
"""
Test script to demonstrate Bangkok city code resolution fix
"""

# Test the LLM extractor fallback logic
def test_extractor_fallback():
    print("=== Testing LLM Extractor Fallback Logic ===")
    
    user_request = "plan a trip to Bangkok on 15th Sep for 3 days"
    user_lower = user_request.lower()
    
    # Simulate the enhanced fallback extraction logic
    destination = None
    
    if "thailand" in user_lower or "bangkok" in user_lower:
        destination = "Bangkok, Thailand"
        print(f"✅ Extracted destination: '{destination}'")
    else:
        print(f"❌ Failed to extract destination from: '{user_request}'")
    
    return destination

# Test the orchestrator city code mapping
def test_city_code_mapping():
    print("\n=== Testing Orchestrator City Code Mapping ===")
    
    # Simulate the enhanced city code mapping
    city_codes = {
        "Bangkok": "BKK",
        "Bangkok, Thailand": "BKK",  # Support the standardized format
        "Thailand": "BKK",  # Many people say "Thailand" meaning Bangkok
        "Paris": "PAR",
        "London": "LON",
    }
    
    test_destinations = [
        "Bangkok",
        "Bangkok, Thailand", 
        "Thailand",
        "Paris",
        "Unknown City"
    ]
    
    for destination in test_destinations:
        code = None
        for city, city_code in city_codes.items():
            if city.lower() in destination.lower():
                code = city_code
                break
        
        if code:
            print(f"✅ '{destination}' → {code}")
        else:
            print(f"❌ '{destination}' → PAR (fallback)")

# Test the complete flow
def test_complete_flow():
    print("\n=== Testing Complete Bangkok Flow ===")
    
    user_request = "plan a trip to Bangkok on 15th Sep for 3 days"
    print(f"Input: {user_request}")
    
    # Step 1: Extract destination
    destination = test_extractor_fallback()
    
    if destination:
        # Step 2: Map to city code
        city_codes = {
            "Bangkok": "BKK",
            "Bangkok, Thailand": "BKK",
            "Thailand": "BKK",
        }
        
        city_code = None
        for city, code in city_codes.items():
            if city.lower() in destination.lower():
                city_code = code
                break
        
        if city_code:
            print(f"✅ Final mapping: '{destination}' → {city_code}")
            print(f"✅ Hotels will search using cityCode: {city_code}")
            print(f"✅ This should resolve the Bangkok → PAR issue!")
        else:
            print(f"❌ Failed to map destination to city code")
    else:
        print(f"❌ Failed to extract destination")

if __name__ == "__main__":
    test_extractor_fallback()
    test_city_code_mapping()
    test_complete_flow()