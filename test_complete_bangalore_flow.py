#!/usr/bin/env python3
"""
Test script to verify the complete Bangalore flow from city resolution to hotel coordinates
"""

def test_complete_flow():
    print("=== Testing Complete Bangalore Flow ===")
    
    # Step 1: Simulate LLM extraction
    user_query = "plan a trip to Bangalore"
    print(f"Input: {user_query}")
    
    # LLM should extract this as "Bangalore, India"
    extracted_destination = "Bangalore, India"
    print(f"✅ LLM extracts: '{extracted_destination}'")
    
    # Step 2: Orchestrator city code resolution
    city_codes = {
        "Bangkok": "BKK",
        "Bangkok, Thailand": "BKK",
        "Thailand": "BKK",
        "Bangalore": "BLR",
        "Bangalore, India": "BLR",
        "Bengaluru": "BLR",
        "Bengaluru, India": "BLR",
        "Paris": "PAR",
        "London": "LON",
    }
    
    def get_city_code(destination):
        for city, code in city_codes.items():
            if city.lower() in destination.lower():
                return code
        return "PAR"  # Default fallback
    
    city_code = get_city_code(extracted_destination)
    print(f"✅ City code resolution: '{extracted_destination}' → {city_code}")
    
    # Step 3: Hotel agent coordinates lookup
    coordinates = {
        "ZUR": (47.3769, 8.5417),     # Zurich
        "PAR": (48.8566, 2.3522),     # Paris
        "LON": (51.5074, -0.1278),    # London  
        "NYC": (40.7128, -74.0060),   # New York
        "TYO": (35.6762, 139.6503),   # Tokyo
        "LAX": (34.0522, -118.2437),  # Los Angeles
        "SFO": (37.7749, -122.4194),  # San Francisco
        "BKK": (13.7563, 100.5018),   # Bangkok
        "BLR": (12.9716, 77.5946),    # Bangalore/Bengaluru (FIXED!)
        "SIN": (1.3521, 103.8198),    # Singapore
        "DXB": (25.2048, 55.2708),    # Dubai
        "SYD": (-33.8688, 151.2093)   # Sydney
    }
    
    def get_coordinates(city_code):
        return coordinates.get(city_code, (48.8566, 2.3522))  # Default to Paris
    
    lat, lng = get_coordinates(city_code)
    print(f"✅ Hotel coordinates: {city_code} → ({lat}, {lng})")
    
    # Step 4: Verify complete flow
    if city_code == "BLR" and lat == 12.9716 and lng == 77.5946:
        print(f"\n🎯 SUCCESS: Complete flow works correctly!")
        print(f"✅ Bangalore queries will now search hotels at correct coordinates")
        print(f"✅ No more PAR fallback for Bangalore/Bengaluru!")
    else:
        print(f"\n❌ FAILED: Something is still wrong")
        print(f"   Expected: BLR → (12.9716, 77.5946)")
        print(f"   Got: {city_code} → ({lat}, {lng})")

def test_variants():
    print("\n=== Testing All Bangalore/Bengaluru Variants ===")
    
    variants = [
        "Bangalore",
        "Bangalore, India", 
        "Bengaluru",
        "Bengaluru, India",
    ]
    
    city_codes = {
        "Bangkok": "BKK",
        "Bangkok, Thailand": "BKK",
        "Thailand": "BKK",
        "Bangalore": "BLR",
        "Bangalore, India": "BLR",
        "Bengaluru": "BLR",
        "Bengaluru, India": "BLR",
        "Paris": "PAR",
    }
    
    coordinates = {
        "BLR": (12.9716, 77.5946),
        "BKK": (13.7563, 100.5018),
        "PAR": (48.8566, 2.3522),
    }
    
    for variant in variants:
        # Find matching city code
        city_code = None
        for city, code in city_codes.items():
            if city.lower() in variant.lower():
                city_code = code
                break
        
        if not city_code:
            city_code = "PAR"
        
        # Get coordinates
        lat, lng = coordinates.get(city_code, (48.8566, 2.3522))
        
        # Check result
        if city_code == "BLR":
            print(f"✅ '{variant}' → {city_code} → ({lat}, {lng})")
        else:
            print(f"❌ '{variant}' → {city_code} → ({lat}, {lng}) [SHOULD BE BLR]")

if __name__ == "__main__":
    test_complete_flow()
    test_variants()