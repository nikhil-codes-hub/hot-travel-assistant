from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    """Get database URL - SQLite by default for MVP simplicity"""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return database_url
    
    # Default to SQLite for MVP - simple, portable, zero-configuration
    print("🗄️  Using SQLite database (perfect for MVP!)")
    return "sqlite:///./hot_travel_assistant.db"

DATABASE_URL = get_database_url()
print(f"📁 Database: {DATABASE_URL}")

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()