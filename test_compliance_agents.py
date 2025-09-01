#!/usr/bin/env python3
"""
Test script for the refined compliance agents (Visa and Health)
"""
import asyncio
import sys
from agents.compliance.visa import VisaAgent
from agents.compliance.health import HealthAgent

async def test_visa_agent():
    """Test the Visa Agent"""
    print("🛂 Testing Visa Agent...")
    
    try:
        agent = VisaAgent()
        
        # Test with Japan and US nationality
        test_input = {
            "destination": "japan",
            "nationality": "US"
        }
        
        result = await agent.execute(test_input, "test_session_visa")
        
        print("✅ Visa Agent Test Result:")
        print(f"   Destination: {result['data']['destination']}")
        print(f"   Nationality: {result['data']['nationality']}")
        visa_req = result['data']['visa_requirements']
        print(f"   Visa Required: {visa_req.get('visa_required', 'unknown')}")
        print(f"   Mode: {visa_req.get('mode', 'unknown')}")
        if 'duration' in visa_req:
            print(f"   Duration: {visa_req['duration']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Visa Agent Test Failed: {e}")
        return False

async def test_health_agent():
    """Test the Health Agent"""
    print("\n⚕️ Testing Health Agent...")
    
    try:
        agent = HealthAgent()
        
        # Test with Brazil
        test_input = {
            "destination": "brazil"
        }
        
        result = await agent.execute(test_input, "test_session_health")
        
        print("✅ Health Agent Test Result:")
        print(f"   Destination: {result['data']['destination']}")
        health_req = result['data']['health_requirements']
        print(f"   Mode: {health_req.get('mode', 'unknown')}")
        
        if 'vaccinations_recommended' in health_req:
            print(f"   Recommended Vaccines: {health_req['vaccinations_recommended']}")
        if 'malaria_risk' in health_req:
            print(f"   Malaria Risk: {health_req['malaria_risk']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health Agent Test Failed: {e}")
        return False

async def main():
    print("🧪 Testing Compliance Agents for HOT Travel Assistant\n")
    
    visa_success = await test_visa_agent()
    health_success = await test_health_agent()
    
    print(f"\n📊 Test Results:")
    print(f"   Visa Agent: {'✅ PASS' if visa_success else '❌ FAIL'}")
    print(f"   Health Agent: {'✅ PASS' if health_success else '❌ FAIL'}")
    
    if visa_success and health_success:
        print(f"\n🎉 All tests passed! Compliance agents are working correctly.")
        return 0
    else:
        print(f"\n💥 Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)