from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    """Get database URL with fallback support"""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return database_url
    
    # Try to detect if MySQL is available
    try:
        import pymysql
        # Try to connect to check if MySQL server is running
        try:
            connection = pymysql.connect(
                host='localhost',
                user='root',
                password='password',
                database='hot_travel_assistant'
            )
            connection.close()
            print("✅ MySQL detected and available")
            return "mysql+pymysql://root:password@localhost:3306/hot_travel_assistant"
        except:
            print("⚠️  MySQL not available, falling back to SQLite")
            return "sqlite:///./hot_travel_assistant.db"
    except ImportError:
        print("⚠️  PyMySQL not installed, using SQLite")
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