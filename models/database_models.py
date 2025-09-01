from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import datetime

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(255), unique=True, index=True)
    nationality = Column(String(100))
    passport_number_hash = Column(String(255))
    loyalty_tier = Column(String(50))
    preferences = Column(JSON)
    travel_history = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SearchSession(Base):
    __tablename__ = "search_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True)
    customer_id = Column(String(255))
    original_request = Column(Text)
    extracted_requirements = Column(JSON)
    search_results = Column(JSON)
    final_itinerary = Column(JSON)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("search_sessions.session_id"))
    agent_name = Column(String(100))
    input_data = Column(JSON)
    output_data = Column(JSON)
    execution_time_ms = Column(Integer)
    status = Column(String(50), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)