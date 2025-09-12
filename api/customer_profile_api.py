#!/usr/bin/env python3
"""
Simple customer profile API for testing
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_db
from services.customer_profile_service import CustomerProfileService
import structlog

logger = structlog.get_logger()

# Create router
router = APIRouter()

# Pydantic models
class CustomerData(BaseModel):
    email: str
    first_name: str = None
    last_name: str = None

class TravelHistoryData(BaseModel):
    email: str
    destination: str
    country: str = None
    city: str = None
    event_name: str = None
    event_type: str = None
    travel_date_start: str  # YYYY-MM-DD format
    travel_date_end: str = None  # YYYY-MM-DD format
    season: str = None
    budget_range: str = None
    travel_style: str = None
    satisfaction_rating: int = None
    notes: str = None

@router.get("/")
async def root():
    return {"message": "Customer Profile API", "version": "1.0.0"}

@router.get("/health")
async def health_check(db = Depends(get_db)):
    """Health check endpoint"""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")

@router.get("/customer/profile/{email}")
async def get_customer_profile(email: str, db = Depends(get_db)):
    """Get customer profile with personalized suggestions"""
    try:
        service = CustomerProfileService()
        suggestions = service.generate_personalized_suggestions(db, email)
        
        return {
            "success": True,
            "data": suggestions
        }
    except Exception as e:
        logger.error("Error getting customer profile", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/customer/profile/")
async def create_customer_profile(customer_data: CustomerData, db = Depends(get_db)):
    """Create or update customer profile"""
    try:
        service = CustomerProfileService()
        customer = service.get_or_create_customer(
            db,
            customer_data.email,
            customer_data.first_name,
            customer_data.last_name
        )
        
        return {
            "success": True,
            "customer": customer.to_dict()
        }
    except Exception as e:
        logger.error("Error creating customer profile", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/customer/travel-history/")
async def add_travel_history(history_data: TravelHistoryData, db = Depends(get_db)):
    """Add travel history for customer"""
    try:
        service = CustomerProfileService()
        from datetime import datetime
        
        # Convert the history data to dict and parse dates
        history_dict = history_data.dict()
        if history_dict['travel_date_start']:
            history_dict['travel_date_start'] = datetime.strptime(
                history_dict['travel_date_start'], '%Y-%m-%d'
            ).date()
        if history_dict['travel_date_end']:
            history_dict['travel_date_end'] = datetime.strptime(
                history_dict['travel_date_end'], '%Y-%m-%d' 
            ).date()
            
        history = service.add_travel_history(db, history_dict["email"], history_dict)
        
        return {
            "success": True,
            "travel_history": history.to_dict()
        }
    except Exception as e:
        logger.error("Error adding travel history", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }

# Export router for main app to include
export_router = router