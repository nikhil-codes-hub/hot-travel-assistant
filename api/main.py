from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

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

@app.post("/travel/search", response_model=TravelResponse)
async def search_travel(request: TravelRequest, db = Depends(get_db)):
    """
    Process a travel search request through the AI agent system
    """
    try:
        session_id = str(uuid.uuid4())
        
        # Initialize orchestrator
        orchestrator = TravelOrchestrator(db)
        
        # Determine customer identifier
        customer_id = request.email_id or request.customer_id or f"guest_{session_id[:8]}"
        
        # Prepare input data
        input_data = {
            "user_request": request.user_request,
            "customer_id": customer_id,
            "email_id": request.email_id,
            "nationality": request.nationality,
            "passport_number": request.passport_number,
            "session_id": session_id
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)