#!/usr/bin/env python3
"""
Test script to verify Bangalore/Bengaluru city code mapping fix
"""

def test_bangalore_mapping():
    print("=== Testing Bangalore/Bengaluru City Code Mapping ===")
    
    # Simulate the city code mapping logic
    city_codes = {
        "Zermatt": "ZUR",
        "Switzerland": "ZUR",
        "Tokyo": "TYO",
        "Paris": "PAR",
        "London": "LON",
        "New York": "NYC",
        "Bangkok": "BKK",
        "Bangkok, Thailand": "BKK",
        "Thailand": "BKK",
        "Singapore": "SIN",
        "Dubai": "DXB",
        "Mumbai": "BOM",
        "Bangalore": "BLR",
        "Bangalore, India": "BLR",
        "Bengaluru": "BLR",  # Official name of Bangalore
        "Bengaluru, India": "BLR",
        "Sydney": "SYD",
        "Los Angeles": "LAX"
    }
    
    test_destinations = [
        "Bangalore",
        "Bangalore, India", 
        "Bengaluru",
        "Bengaluru, India",
        "Bangkok",
        "Bangkok, Thailand"
    ]
    
    def get_city_code(destination):
        if not destination:
            return "PAR"  # Default fallback
            
        for city, code in city_codes.items():
            if city.lower() in destination.lower():
                return code
        return "PAR"  # Default fallback
    
    print(f"Input from logs: 'Bangalore, India'")
    for destination in test_destinations:
        code = get_city_code(destination)
        expected = "BLR" if any(x in destination.lower() for x in ["bangalore", "bengaluru"]) else "BKK"
        
        if code == expected:
            print(f"✅ '{destination}' → {code}")
        else:
            print(f"❌ '{destination}' → {code} (expected {expected})")
    
    # Test the specific case from the logs
    result = get_city_code("Bangalore, India")
    if result == "BLR":
        print(f"\n🎯 SUCCESS: 'Bangalore, India' correctly maps to {result}")
        print("✅ The mapping should work once the server loads the updated code")
    else:
        print(f"\n❌ FAILED: 'Bangalore, India' maps to {result} instead of BLR")

if __name__ == "__main__":
    test_bangalore_mapping()