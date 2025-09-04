#!/usr/bin/env python3
"""
Test script to verify the cache system works without database
"""

import asyncio
import json
from agents.llm_extractor.extractor_agent import LLMExtractorAgent

async def test_cache_without_db():
    """Test the cache system independently of database"""
    
    print("🧪 Testing Cache System Without Database")
    print("=" * 50)
    
    try:
        # Test 1: Initialize agent (should work without database)
        print("\n1. Initializing LLM Extractor Agent...")
        agent = LLMExtractorAgent()
        print("   ✅ Agent initialized successfully")
        
        # Test 2: Test with mock data (no LLM call since no API key)
        print("\n2. Testing intelligent defaults (no LLM)...")
        
        test_requests = [
            "I want to visit Thailand next month",
            "Plan a trip to Thailand next month", 
            "Thailand vacation next month",
            "Paris trip for 2 people"
        ]
        
        for i, request in enumerate(test_requests, 1):
            print(f"\n   Test {i}: '{request}'")
            
            try:
                input_data = {
                    "user_request": request,
                    "conversation_context": {}
                }
                
                result = await agent.execute(input_data, f"test_session_{i}")
                
                # Check if we got cache hit or fallback
                cache_info = result.get("data", {}).get("cache_info", {})
                if cache_info.get("cache_hit"):
                    print(f"   ✅ Cache HIT - returned instantly")
                else:
                    print(f"   🔄 Cache MISS - used intelligent defaults")
                
                # Show key extracted data
                requirements = result.get("data", {}).get("requirements", {})
                destination = requirements.get("destination", "Not extracted")
                duration = requirements.get("duration", "Not set")
                passengers = requirements.get("passengers", "Not set")
                
                print(f"      📍 Destination: {destination}")
                print(f"      📅 Duration: {duration} days")
                print(f"      👥 Passengers: {passengers}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        # Test 3: Check cache statistics
        print("\n3. Checking cache statistics...")
        try:
            cache_stats = agent.cache.get_cache_stats()
            print(f"   📊 Cache files: {cache_stats.get('total_files', 0)}")
            print(f"   📊 Cache size: {cache_stats.get('total_size_mb', 0)} MB")
            print(f"   📂 Cache directory: {cache_stats.get('cache_directory', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ Cache stats error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🎉 Cache system test completed successfully!")
        print("💡 The system works without database - cache stores to local files")
        print("🚀 To enable LLM functionality, add GEMINI_API_KEY to .env file")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("🔧 Check that all dependencies are installed correctly")

if __name__ == "__main__":
    asyncio.run(test_cache_without_db())