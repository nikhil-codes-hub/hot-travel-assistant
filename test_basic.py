#!/usr/bin/env python3
"""
Basic test script to verify core setup works
"""
import sys
import time

def test_basic_imports():
    """Test basic imports"""
    print("Testing basic imports...")
    
    try:
        import sqlalchemy
        print("✅ SQLAlchemy import successful!")
        
        import pymysql
        print("✅ PyMySQL import successful!")
        
        import fastapi
        print("✅ FastAPI import successful!")
        
        from config.database import engine, Base
        print("✅ Database config import successful!")
        
        from models.database_models import UserProfile, SearchSession
        print("✅ Database models import successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_mysql_connection():
    """Test MySQL connection"""
    try:
        from config.database import engine
        from models.database_models import Base
        
        print("Testing MySQL connection...")
        
        # Wait for MySQL to be ready
        max_retries = 10
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
                time.sleep(3)
        
        # Create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_api_startup():
    """Test FastAPI app creation"""
    try:
        from fastapi import FastAPI
        
        print("Testing FastAPI app creation...")
        app = FastAPI(title="Test App")
        print("✅ FastAPI app created successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    print("🚀 HOT Intelligent Travel Assistant - Basic Setup Test")
    print("=" * 55)
    
    # Test basic imports
    if not test_basic_imports():
        sys.exit(1)
    
    # Test database
    if not test_mysql_connection():
        sys.exit(1)
    
    # Test API
    if not test_api_startup():
        sys.exit(1)
    
    print("\n🎉 Basic tests passed! Core setup is working.")
    print("\nNext steps:")
    print("1. Add your Google Cloud credentials to .env")
    print("2. Test API: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
    print("3. Visit http://localhost:8000/docs")

if __name__ == "__main__":
    main()