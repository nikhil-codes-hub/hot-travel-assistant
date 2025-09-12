#!/usr/bin/env python3
"""
Simple test for visa and health API endpoints
"""
import asyncio
import json
from agents.compliance.visa_agent import VisaRequirementAgent
from agents.compliance.health_agent import HealthAdvisoryAgent

async def test_visa_agent():
    """Test visa requirements agent"""
    print("🧪 Testing Visa Requirements Agent...")
    
    agent = VisaRequirementAgent()
    input_data = {
        "origin_country": "JP",
        "destination_country": "CA", 
        "travel_purpose": "tourism",
        "passport_type": "regular"
    }
    
    try:
        result = await agent.execute(input_data, "test_session")
        print("✅ Visa Agent Success:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ Visa Agent Error: {e}")
        return None

async def test_health_agent():
    """Test health advisory agent"""
    print("\n🧪 Testing Health Advisory Agent...")
    
    agent = HealthAdvisoryAgent()
    input_data = {
        "destination_country": "CA",
        "origin_country": "JP", 
        "travel_activities": "tourism",
        "traveler_profile": {
            "age_group": "adult",
            "origin": "JP"
        }
    }
    
    try:
        result = await agent.execute(input_data, "test_session")
        print("✅ Health Agent Success:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ Health Agent Error: {e}")
        return None

async def main():
    """Run tests"""
    print("🚀 Starting Visa & Health API Tests...\n")
    
    visa_result = await test_visa_agent()
    health_result = await test_health_agent()
    
    print(f"\n📊 Test Summary:")
    print(f"• Visa Agent: {'✅ Success' if visa_result else '❌ Failed'}")
    print(f"• Health Agent: {'✅ Success' if health_result else '❌ Failed'}")

if __name__ == "__main__":
    asyncio.run(main())