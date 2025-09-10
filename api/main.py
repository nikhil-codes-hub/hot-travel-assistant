from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

from api.send_email import send_message
from config.database import get_db, engine
from models.database_models import Base
from orchestrator.travel_orchestrator import TravelOrchestrator

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HOT Intelligent Travel Assistant",
    description="Agentic AI Travel Assistant for House of Travel",
    version="1.0.0"
)

# # ---------------------- Models ---------------------- #
class Flight(BaseModel):
    rank: int
    airline: Optional[str]
    price: Optional[str]
    route: Optional[str]
    connections: Optional[int]
    recommendation_reason: Optional[str]

class Hotel(BaseModel):
    name: Optional[str]
    price_per_night: Optional[str]
    location: Optional[str]
    room_type: Optional[str]

class TripDetails(BaseModel):
    destination: str
    departure_date: str
    return_date: Optional[str]
    duration: Optional[int]
    passengers: Optional[int]
    travel_class: Optional[str]
    budget: Optional[float]
    budget_currency: Optional[str]

class Customer(BaseModel):
    email: str
    name: str
    loyalty_tier: Optional[str]
    nationality: Optional[str]
    booking_history: Optional[int]

class SessionInfo(BaseModel):
    session_id: str
    generated_at: str
    agent_notes: Optional[str]

class EmailData(BaseModel):
    customer: Customer
    trip_details: TripDetails
    flights: List[Flight] = []
    hotels: List[Hotel] = []
    session_info: Optional[SessionInfo]

class SendMailResponse(BaseModel):
    success: bool
    message: str

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class TravelRequest(BaseModel):
    user_request: str
    customer_id: Optional[str] = None  # Keep for backward compatibility
    email_id: Optional[str] = None     # New preferred field
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    session_id: Optional[str] = None   # For conversation continuity
    conversation_context: Optional[Dict[str, Any]] = None  # Accumulated requirements

class TravelResponse(BaseModel):
    session_id: str
    status: str
    data: Dict[str, Any]
    timestamp: str

@app.get("/")
async def root():
    return {"message": "HOT Intelligent Travel Assistant API", "version": "1.0.0"}

@app.get("/health")
async def health_check(db = Depends(get_db)):
    """Health check endpoint with database connection test"""
    try:
        from sqlalchemy import text
        # Test database connection
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "api_version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")
 
@app.post("/travel/sendmail", response_model=SendMailResponse)
async def sendmail(email_data: EmailData):
    try:
        # convert Pydantic model to dict
        print("the emaildata before",email_data)
        # email_data = email_data.dict()
        print("fligents details after",email_data.customer.email)
        send_message(email_data)
        return {"success": True, "message": "✅ Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Failed to send email: {str(e)}")

@app.post("/travel/search", response_model=TravelResponse)
async def search_travel(request: TravelRequest, db = Depends(get_db)):
    """
    Process a travel search request through the AI agent system
    """
    try:
        # Use existing session_id if provided, otherwise create new one
        session_id = request.session_id or str(uuid.uuid4())
        
        # Initialize orchestrator
        orchestrator = TravelOrchestrator(db)
        
        # Determine customer identifier
        customer_id = request.email_id or request.customer_id or f"guest_{session_id[:8]}"
        
        # Prepare input data with conversation context
        input_data = {
            "user_request": request.user_request,
            "customer_id": customer_id,
            "email_id": request.email_id,
            "nationality": request.nationality,
            "passport_number": request.passport_number,
            "session_id": session_id,
            "conversation_context": request.conversation_context or {}
        }
        
        # Execute orchestrator
        result = await orchestrator.process_travel_request(input_data, session_id)
        
        return TravelResponse(
            session_id=session_id,
            status="completed",
            data=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/travel/session/{session_id}")
async def get_session(session_id: str, db = Depends(get_db)):
    """
    Retrieve session information and results
    """
    try:
        # TODO: Implement session retrieval from database
        return {"session_id": session_id, "status": "not_implemented"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/travel/confirm/{session_id}")
async def confirm_booking(session_id: str, db = Depends(get_db)):
    """
    Confirm booking and trigger compliance agents
    """
    try:
        orchestrator = TravelOrchestrator(db)
        result = await orchestrator.process_confirmation(session_id)
        
        return TravelResponse(
            session_id=session_id,
            status="confirmed",
            data=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/profile/{customer_id}")
async def get_user_profile(customer_id: str, db = Depends(get_db)):
    """
    Retrieve user profile information by customer_id
    """
    try:
        from agents.user_profile import UserProfileAgent
        
        agent = UserProfileAgent()
        result = await agent.run({"customer_id": customer_id}, "profile_lookup")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/profile-by-email/{email_id}")
async def get_user_profile_by_email(email_id: str, db = Depends(get_db)):
    """
    Retrieve user profile information by email_id
    """
    try:
        from agents.user_profile import UserProfileAgent
        
        agent = UserProfileAgent()
        result = await agent.run({"email_id": email_id}, "profile_lookup")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/database/tables")
async def list_tables(db = Depends(get_db)):
    """List database tables for verification"""
    try:
        from sqlalchemy import text
        tables = db.execute(text("SHOW TABLES")).fetchall()
        return {
            "tables": [table[0] for table in tables],
            "database": "hot_travel_assistant",
            "connection": "mysql"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/database/users")
async def list_users(db = Depends(get_db)):
    """List recent user profiles from database"""
    try:
        from models.database_models import UserProfile
        users = db.query(UserProfile).limit(10).all()
        return {
            "count": len(users),
            "users": [
                {
                    "customer_id": user.customer_id,
                    "nationality": user.nationality,
                    "loyalty_tier": user.loyalty_tier,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                for user in users
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/preferences/{customer_id}")
async def analyze_customer_preferences(customer_id: str, query: str = None, db = Depends(get_db)):
    """
    Analyze customer travel preferences using AI-powered analysis
    """
    try:
        from agents.user_profile import UserProfileAgent
        
        agent = UserProfileAgent()
        result = await agent.analyze_preferences(customer_id, query)
        
        return {
            "customer_id": customer_id,
            "analysis": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/recommendations/{customer_id}")
async def get_travel_recommendations(customer_id: str, db = Depends(get_db)):
    """
    Get personalized travel recommendations for a customer
    """
    try:
        from agents.user_profile import UserProfileAgent
        
        agent = UserProfileAgent()
        result = await agent.get_travel_recommendations(customer_id)
        
        return {
            "customer_id": customer_id,
            "recommendations": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/travel/visa-requirements")
async def get_visa_requirements(
    origin_country: str, 
    destination_country: str, 
    travel_purpose: str = "tourism",
    passport_type: str = "regular",
    session_id: str = None
):
    """
    Get visa requirements using Amadeus API and visa agent
    """
    try:
        from agents.compliance.visa_agent import VisaRequirementAgent
        
        agent = VisaRequirementAgent()
        input_data = {
            "origin_country": origin_country.upper(),
            "destination_country": destination_country.upper(),
            "travel_purpose": travel_purpose,
            "passport_type": passport_type
        }
        
        result = await agent.execute(input_data, session_id or str(uuid.uuid4()))
        
        return {
            "visa_requirements": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/travel/health-advisory")
async def get_health_advisory(
    destination_country: str,
    origin_country: str = "JP",
    session_id: str = None,
    travel_activities: str = "tourism"
):
    """
    Get health advisory information for destination
    """
    try:
        from agents.compliance.health_agent import HealthAdvisoryAgent
        
        agent = HealthAdvisoryAgent()
        input_data = {
            "destination_country": destination_country.upper(),
            "origin_country": origin_country.upper(),
            "travel_activities": travel_activities,
            "traveler_profile": {
                "age_group": "adult",
                "origin": origin_country.upper()
            }
        }
        
        result = await agent.execute(input_data, session_id or str(uuid.uuid4()))
        
        return {
            "health_advisory": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def log_ai_configuration():
    """Log current AI configuration for debugging"""
    import os
    import logging
    
    logger = logging.getLogger("uvicorn.error")
    
    logger.info("🔧 SYSTEM STARTUP - Vertex AI Configuration Check:")
    
    # Only using Vertex AI
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    
    logger.info("📊 AI Provider: Vertex AI (Google Cloud)")
    
    if project_id:
        logger.info(f"✅ Vertex AI Project: {project_id}")
    else:
        logger.error("❌ GOOGLE_CLOUD_PROJECT not set")
        logger.error("💡 Please set GOOGLE_CLOUD_PROJECT in your .env file")
        
    if location:
        logger.info(f"✅ Vertex AI Location: {location}")
    else:
        logger.warning("⚠️  VERTEX_AI_LOCATION not set, using default: us-central1")
        
    # Check for service account
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        logger.info(f"✅ Service Account: {creds_path}")
    else:
        logger.warning("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
        logger.warning("🔧 Using Application Default Credentials (ADC)")
        logger.info("💡 Ensure you're authenticated with: gcloud auth application-default login")
    
    # Check Amadeus API
    amadeus_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    if amadeus_id and amadeus_secret:
        logger.info("✅ Amadeus API: Configured")
    else:
        logger.warning("⚠️  Amadeus API not fully configured")
    
    logger.info("🚀 Starting HOT Travel Assistant API...")

if __name__ == "__main__":
    import uvicorn
    
    # Log AI configuration at startup
    log_ai_configuration()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)