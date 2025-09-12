#!/usr/bin/env python3
"""
Simple test script to verify the setup works
"""
import sys
import os
import time

def test_mysql_connection():
    """Test MySQL connection"""
    try:
        from config.database import engine
        from models.database_models import Base
        
        print("Testing MySQL connection...")
        
        # Wait for MySQL to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                connection = engine.connect()
                connection.close()
                print("✅ MySQL connection successful!")
                break
            except Exception as e:
                if i == max_retries - 1:
                    print(f"❌ MySQL connection failed after {max_retries} retries: {e}")
                    return False
                print(f"⏳ Waiting for MySQL... ({i+1}/{max_retries})")
                time.sleep(2)
        
        # Create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_imports():
    """Test that all key modules can be imported"""
    print("Testing imports...")
    
    try:
        from agents.llm_extractor import LLMExtractorAgent
        print("✅ LLM Extractor Agent import successful!")
        
        from agents.user_profile import UserProfileAgent
        print("✅ User Profile Agent import successful!")
        
        from orchestrator import TravelOrchestrator
        print("✅ Travel Orchestrator import successful!")
        
        from api.main import app
        print("✅ FastAPI app import successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    print("🚀 HOT Intelligent Travel Assistant - Setup Test")
    print("=" * 50)
    
    # Test imports first
    if not test_imports():
        sys.exit(1)
    
    # Test database
    if not test_mysql_connection():
        sys.exit(1)
    
    print("\n🎉 All tests passed! Setup is working correctly.")
    print("\nNext steps:")
    print("1. Add your API keys to .env file")
    print("2. Run the API: uvicorn api.main:app --reload")
    print("3. Visit http://localhost:8000/docs for API documentation")

if __name__ == "__main__":
    main()