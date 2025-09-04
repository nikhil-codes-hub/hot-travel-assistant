from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from config.database import get_db, engine
from models.database_models import Base
from orchestrator.travel_orchestrator import TravelOrchestrator

# Create database tables (optional - cache system works without DB)
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️  Database connection failed: {e}")
    print("🔄 Cache system will work without database (file-based only)")

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

@app.post("/travel/search-simple")
async def search_travel_simple(request: TravelRequest):
    """
    Process a travel search request using LLM with cache (works without database)
    """
    try:
        # Use existing session_id if provided, otherwise create new one
        session_id = request.session_id or str(uuid.uuid4())
        
        # Test the LLM extractor with cache
        from agents.llm_extractor.extractor_agent import LLMExtractorAgent
        
        agent = LLMExtractorAgent()
        
        input_data = {
            "user_request": request.user_request,
            "conversation_context": request.conversation_context or {}
        }
        
        # Execute with cache
        result = await agent.execute(input_data, session_id)
        
        return {
            "session_id": session_id,
            "status": "completed",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/cache/stats")
async def get_cache_stats():
    """
    Get LLM cache statistics and performance metrics
    """
    try:
        from agents.cache.llm_cache import LLMCache
        
        # Get stats for different cache directories
        cache_stats = {}
        
        # Main LLM extractor cache
        extractor_cache = LLMCache(cache_dir="cache/llm_responses")
        cache_stats["extractor_cache"] = extractor_cache.get_cache_stats()
        
        # Destination discovery cache
        destination_cache = LLMCache(cache_dir="cache/llm_responses/destination_discovery")
        cache_stats["destination_discovery_cache"] = destination_cache.get_cache_stats()
        
        # Calculate totals
        total_files = sum(stats.get("total_files", 0) for stats in cache_stats.values())
        total_size_mb = sum(stats.get("total_size_mb", 0) for stats in cache_stats.values())
        
        return {
            "cache_statistics": cache_stats,
            "summary": {
                "total_cache_files": total_files,
                "total_cache_size_mb": total_size_mb,
                "cache_enabled": True,
                "cache_duration_hours": 24
            },
            "performance_benefits": {
                "api_cost_savings": "Cached responses avoid repeated LLM API calls",
                "response_time_improvement": "Cached responses return instantly",
                "consistency": "Same queries return consistent travel planning data"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear-expired")
async def clear_expired_cache():
    """
    Clear expired cache files to free up storage
    """
    try:
        from agents.cache.llm_cache import LLMCache
        
        # Clear expired files from different caches
        extractor_cache = LLMCache(cache_dir="cache/llm_responses")
        extractor_removed = extractor_cache.clear_expired_cache()
        
        destination_cache = LLMCache(cache_dir="cache/llm_responses/destination_discovery")
        destination_removed = destination_cache.clear_expired_cache()
        
        total_removed = extractor_removed + destination_removed
        
        return {
            "status": "completed",
            "files_removed": {
                "extractor_cache": extractor_removed,
                "destination_discovery_cache": destination_removed,
                "total": total_removed
            },
            "message": f"Removed {total_removed} expired cache files",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)