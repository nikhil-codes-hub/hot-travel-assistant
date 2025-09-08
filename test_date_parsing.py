#!/usr/bin/env python3
"""
Test script to verify date parsing for '15th Sep' and similar patterns
"""

import re
from datetime import datetime

def test_date_parsing():
    print("=== Testing Date Parsing Patterns ===")
    
    # Test input
    user_request = "plan a trip to Bangkok on 15th Sep for 3 days"
    user_lower = user_request.lower()
    current_year = datetime.now().year
    
    print(f"Input: {user_request}")
    print(f"Current year: {current_year}")
    
    # Date patterns (simplified from the extractor)
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
        # Patterns without year - default to current year
        r'(?:sep|september)\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*,?\s*\d{4})',  # "Sep 15th" (no year)
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:sep|september)(?!\s*,?\s*\d{4})',  # "15th September" (no year)
        # Patterns with year
        r'(?:sep|september)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',  # "Sep 15th 2025"
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?:sep|september)\s*,?\s*(\d{4})',  # "15th September 2025"
    ]
    
    departure_date = None
    
    for i, pattern in enumerate(date_patterns):
        print(f"\nTesting pattern {i+1}: {pattern}")
        date_match = re.search(pattern, user_lower)
        if date_match:
            print(f"  ✅ Match found: {date_match.groups()}")
            
            if len(date_match.groups()) == 2:  # Month day year format
                day = date_match.group(1)
                year = date_match.group(2)
                print(f"  📅 Extracted: day={day}, year={year}")
            elif len(date_match.groups()) == 1:  # Month day format (no year)
                day = date_match.group(1)
                year = str(current_year)
                print(f"  📅 Extracted: day={day}, year={year} (current year)")
            else:
                departure_date = date_match.group(1)
                print(f"  📅 Direct date: {departure_date}")
                break
            
            # Determine month based on pattern matched
            if 'sep' in pattern:
                departure_date = f"{year}-09-{day.zfill(2)}"
                print(f"  ✅ Final date: {departure_date}")
                break
        else:
            print(f"  ❌ No match")
    
    if departure_date:
        print(f"\n🎯 SUCCESS: '15th Sep' parsed as {departure_date}")
        
        # Verify it's September 15, 2025 (not October 8, 2025)
        expected_date = "2025-09-15"
        if departure_date == expected_date:
            print(f"✅ CORRECT: Got expected date {expected_date}")
        else:
            print(f"❌ INCORRECT: Expected {expected_date}, got {departure_date}")
    else:
        print(f"\n❌ FAILED: Could not parse '15th Sep'")
        print(f"💡 This would fall back to 30 days from today: {datetime.now().strftime('%Y-%m-%d')}")

def test_various_date_formats():
    print("\n=== Testing Various Date Formats ===")
    
    test_cases = [
        "plan a trip to Bangkok on 15th Sep for 3 days",
        "visit Thailand on September 15th",
        "travel to Bangkok on Sep 15 2025",
        "go to Thailand on 15th September 2025",
        "plan trip on 2025-09-15",
        "visit on 9/15/2025"
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: '{test_case}'")
        # This would normally call the full extraction logic
        # For now, just check if we can extract the basic pattern
        if "sep" in test_case.lower() and "15" in test_case:
            print("  ✅ Should extract as 2025-09-15")
        else:
            print("  ⚠️  Other date format")

if __name__ == "__main__":
    test_date_parsing()
    test_various_date_formats()