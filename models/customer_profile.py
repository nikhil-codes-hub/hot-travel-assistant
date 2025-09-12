from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional, Dict, Any

Base = declarative_base()

class CustomerProfile(Base):
    __tablename__ = 'customer_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    preferred_language = Column(String(10), default='en')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    travel_history = relationship("CustomerTravelHistory", back_populates="customer", cascade="all, delete-orphan")
    preferences = relationship("CustomerPreference", back_populates="customer", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'preferred_language': self.preferred_language,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CustomerTravelHistory(Base):
    __tablename__ = 'customer_travel_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_email = Column(String(255), ForeignKey('customer_profiles.email'), nullable=False, index=True)
    destination = Column(String(200), nullable=False, index=True)
    country = Column(String(100))
    city = Column(String(100))
    event_name = Column(String(200))
    event_type = Column(String(100), index=True)  # festival, conference, leisure, business
    travel_date_start = Column(Date, index=True)
    travel_date_end = Column(Date)
    season = Column(String(20))  # spring, summer, monsoon, winter
    budget_range = Column(String(50))  # budget, mid-range, luxury
    travel_style = Column(String(100))  # solo, family, group, couple
    satisfaction_rating = Column(Integer)  # 1-5 scale
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    customer = relationship("CustomerProfile", back_populates="travel_history")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_email': self.customer_email,
            'destination': self.destination,
            'country': self.country,
            'city': self.city,
            'event_name': self.event_name,
            'event_type': self.event_type,
            'travel_date_start': self.travel_date_start.isoformat() if self.travel_date_start else None,
            'travel_date_end': self.travel_date_end.isoformat() if self.travel_date_end else None,
            'season': self.season,
            'budget_range': self.budget_range,
            'travel_style': self.travel_style,
            'satisfaction_rating': self.satisfaction_rating,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CustomerPreference(Base):
    __tablename__ = 'customer_preferences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_email = Column(String(255), ForeignKey('customer_profiles.email'), nullable=False, index=True)
    preference_type = Column(String(100), nullable=False, index=True)  # accommodation, transport, activity, cuisine
    preference_value = Column(String(200), nullable=False)
    weight = Column(Integer, default=1)  # Higher weight = stronger preference
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    customer = relationship("CustomerProfile", back_populates="preferences")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_email': self.customer_email,
            'preference_type': self.preference_type,
            'preference_value': self.preference_value,
            'weight': self.weight,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class EventCalendar(Base):
    __tablename__ = 'event_calendar'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(200), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    destination = Column(String(200), nullable=False, index=True)
    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    event_date_start = Column(Date, nullable=False, index=True)
    event_date_end = Column(Date)
    description = Column(Text)
    season = Column(String(20))
    similar_events = Column(Text)  # JSON array of similar event types
    created_at = Column(DateTime, default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        import json
        similar_events_list = []
        if self.similar_events:
            try:
                similar_events_list = json.loads(self.similar_events)
            except:
                similar_events_list = []
        
        return {
            'id': self.id,
            'event_name': self.event_name,
            'event_type': self.event_type,
            'destination': self.destination,
            'country': self.country,
            'city': self.city,
            'event_date_start': self.event_date_start.isoformat() if self.event_date_start else None,
            'event_date_end': self.event_date_end.isoformat() if self.event_date_end else None,
            'description': self.description,
            'season': self.season,
            'similar_events': similar_events_list,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Add composite indexes for better query performance
Index('idx_travel_history_customer_date', CustomerTravelHistory.customer_email, CustomerTravelHistory.travel_date_start)
Index('idx_event_calendar_country_city_date', EventCalendar.country, EventCalendar.city, EventCalendar.event_date_start)
Index('idx_preferences_customer_type', CustomerPreference.customer_email, CustomerPreference.preference_type)