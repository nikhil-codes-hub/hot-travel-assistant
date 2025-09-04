#!/usr/bin/env python3
"""
Test script to demonstrate LLM cache functionality
Run this to verify cache is working properly
"""

import asyncio
from agents.cache.llm_cache import LLMCache

async def test_cache_functionality():
    """Test the LLM cache system with sample travel queries"""
    
    print("🧪 Testing LLM Cache Functionality")
    print("=" * 50)
    
    # Initialize cache
    cache = LLMCache(cache_dir="test_cache", cache_duration_hours=1)
    
    # Test 1: Basic cache storage and retrieval
    print("\n1. Testing basic cache storage and retrieval...")
    
    user_request_1 = "I want to visit Thailand next month"
    context_1 = {"budget": 2000, "passengers": 2}
    
    # Simulate LLM response
    mock_llm_response = {
        "requirements": {
            "destination": "Thailand",
            "duration": 7,
            "budget": 2000,
            "passengers": 2,
            "travel_class": "economy"
        },
        "suggested_defaults": {
            "duration_reasoning": "7 days is optimal for Thailand exploration",
            "budget_reasoning": "$2000 covers accommodation, food, and activities"
        },
        "confidence_score": 0.9
    }
    
    # Store in cache
    stored = cache.store_cached_response(user_request_1, context_1, mock_llm_response)
    print(f"   ✅ Response cached: {stored}")
    
    # Retrieve from cache
    cached_response = cache.get_cached_response(user_request_1, context_1)
    if cached_response:
        print(f"   ✅ Cache hit - retrieved response for Thailand")
        print(f"   📍 Destination: {cached_response['requirements']['destination']}")
    else:
        print(f"   ❌ Cache miss - unexpected")
    
    # Test 2: Similar query variations (should hit cache)
    print("\n2. Testing cache hits for similar queries...")
    
    similar_queries = [
        "visit thailand next month",
        "travel to thailand next month", 
        "thailand trip next month",
        "i want to travel to thailand next month"
    ]
    
    for query in similar_queries:
        cached = cache.get_cached_response(query, context_1)
        result = "✅ Cache HIT" if cached else "❌ Cache MISS"
        print(f"   Query: '{query}' → {result}")
    
    # Test 3: Different context (should miss cache)
    print("\n3. Testing cache miss for different context...")
    
    different_context = {"budget": 5000, "passengers": 4}  # Different context
    cached = cache.get_cached_response(user_request_1, different_context)
    result = "✅ Cache MISS (expected)" if not cached else "❌ Cache HIT (unexpected)"
    print(f"   Same query, different context → {result}")
    
    # Test 4: Cache statistics
    print("\n4. Cache statistics...")
    stats = cache.get_cache_stats()
    print(f"   📊 Total cache files: {stats['total_files']}")
    print(f"   📊 Valid files: {stats['valid_files']}")
    print(f"   📊 Cache size: {stats['total_size_mb']} MB")
    print(f"   📊 Cache directory: {stats['cache_directory']}")
    
    # Test 5: Cache key generation consistency
    print("\n5. Testing cache key consistency...")
    
    # These should generate the same cache key
    test_queries = [
        "thailand vacation",
        "vacation thailand", 
        "Thailand Vacation",
        "i want a thailand vacation please"
    ]
    
    cache_keys = []
    for query in test_queries:
        key = cache._generate_cache_key(query, {})
        cache_keys.append(key)
        print(f"   '{query}' → {key[:8]}...")
    
    # Check if normalization works
    unique_keys = set(cache_keys)
    if len(unique_keys) == 1:
        print(f"   ✅ All queries normalized to same cache key")
    else:
        print(f"   ⚠️  Generated {len(unique_keys)} different keys (normalization needs improvement)")
    
    print("\n" + "=" * 50)
    print("🎉 Cache functionality test completed!")
    
    # Cleanup test cache
    import shutil
    import os
    if os.path.exists("test_cache"):
        shutil.rmtree("test_cache")
        print("🧹 Test cache cleaned up")

if __name__ == "__main__":
    asyncio.run(test_cache_functionality())