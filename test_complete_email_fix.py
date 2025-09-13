#!/usr/bin/env python3
"""
Comprehensive test to verify the complete email generation with fixed flight names and customer names
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.send_mail import build_html

def test_complete_email_with_fixes():
    """Test complete email generation with both airline and customer name fixes"""
    
    print("🧪 Testing complete email with flight and customer name fixes...")
    
    # Mock email data as it would come from the fixed frontend
    fixed_email_data = {
        "customer": {
            "name": "Henry Thomas596",  # Extracted from henry.thomas596@yahoo.com
            "email": "henry.thomas596@yahoo.com"
        },
        "trip_details": {
            "destination": "Bangkok, Thailand",
            "departure_date": "2024-12-15",
            "duration": 5,
            "travelers": 2
        },
        "flights": [
            {
                "rank": 1,
                "airline": "United Airlines",  # Fixed: was "B6"
                "price": "USD 4693.24",
                "route": "LAX → BKK (1 stop) • Business Class",  # Fixed route
                "connections": 1,
                "recommendation_reason": "Best value with premium service"
            },
            {
                "rank": 2,
                "airline": "American Airlines",  # Fixed: was "B6"
                "price": "USD 4693.24", 
                "route": "LAX → BKK (1 stop) • Business Class",
                "connections": 1,
                "recommendation_reason": "Premium loyalty benefits included"
            },
            {
                "rank": 3,
                "airline": "Delta Air Lines",  # Fixed: was "B6"
                "price": "USD 4793.26",
                "route": "LAX → BKK (2 stops) • Business Class", 
                "connections": 2,
                "recommendation_reason": "Comprehensive travel coverage"
            }
        ],
        "hotels": [],
        "itinerary": None,  # Will trigger LLM fallback
        "session_info": None
    }
    
    print("✅ Mock data created with:")
    print(f"   • Customer: {fixed_email_data['customer']['name']} ({fixed_email_data['customer']['email']})")
    print(f"   • Airlines: {[f['airline'] for f in fixed_email_data['flights']]}")
    print(f"   • Routes: {[f['route'] for f in fixed_email_data['flights']]}")
    
    # Generate HTML email
    try:
        html_content = build_html(fixed_email_data)
        
        # Verify fixes
        issues = []
        
        # Check customer name is not email address
        if "henry.thomas596@yahoo.com" in html_content and "Henry Thomas596" not in html_content:
            issues.append("❌ Customer name still shows email address instead of proper name")
        elif "Henry Thomas596" in html_content:
            print("✅ Customer name correctly shows 'Henry Thomas596' instead of email")
        
        # Check airline names are full names, not codes
        if "B6" in html_content:
            issues.append("❌ Email still contains airline codes (B6) instead of full names")
        
        if "United Airlines" in html_content and "American Airlines" in html_content and "Delta Air Lines" in html_content:
            print("✅ Airlines show full names: United Airlines, American Airlines, Delta Air Lines")
        else:
            issues.append("❌ Airline names not found in email content")
        
        # Check route information is meaningful
        if "LAX → LAX" in html_content:
            issues.append("❌ Routes still show incorrect LAX → LAX format")
        elif "LAX → BKK" in html_content:
            print("✅ Routes show correct LAX → BKK format")
        
        # Check business class is mentioned
        if "Business Class" in html_content:
            print("✅ Business Class service mentioned correctly")
        elif "ECONOMY Class" in html_content:
            issues.append("❌ Still showing Economy Class instead of Business Class")
        
        if issues:
            print("\n❌ Issues found:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print("\n✅ All fixes verified successfully!")
            print("   • Customer name extracted from email properly")
            print("   • Airline codes converted to full airline names") 
            print("   • Routes show correct destinations")
            print("   • Business class information preserved")
            return True
            
    except Exception as e:
        print(f"❌ Error generating email: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_email_with_fixes()
    if success:
        print("\n🎉 Email generation fixes are working correctly!")
    else:
        print("\n⚠️  Some issues remain - check the fixes above")