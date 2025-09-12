from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
import sys


# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_db, engine
from models.database_models import Base
from models.customer_profile import Base as CustomerBase
from orchestrator.travel_orchestrator import TravelOrchestrator
from api.send_mail import send_message
import structlog

logger = structlog.get_logger()

# Create database tables for both main app and customer profiles
Base.metadata.create_all(bind=engine)
CustomerBase.metadata.create_all(bind=engine)

app = FastAPI(
    title="HOT Intelligent Travel Assistant",
    description="Agentic AI Travel Assistant for House of Travel",
    version="1.0.0"
)

# Initialize database with sample data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database with sample data if empty"""
    try:
        # Import sample data creation function
        from database.sample_customer_data import create_sample_data
        
        # Check if data already exists
        from models.customer_profile import CustomerProfile
        db = next(get_db())
        
        existing_customers = db.query(CustomerProfile).count()
        if existing_customers == 0:
            logger.info("🗄️ Initializing database with sample data...")
            create_sample_data()
            logger.info("✅ Sample data loaded successfully")
        else:
            logger.info(f"✅ Database already contains {existing_customers} customers")
            
        db.close()
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        # Don't fail startup if sample data fails
        pass

# Add CORS middleware with pattern-based origin matching for Cloud Run
def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed based on patterns"""
    allowed_patterns = [
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "https://*.a.run.app",  # Google Cloud Run pattern
        "https://hot-travel-frontend-*.run.app"  # More specific pattern
    ]
    
    for pattern in allowed_patterns:
        if pattern == origin:
            return True
        # Handle wildcard patterns
        if "*" in pattern:
            import fnmatch
            if fnmatch.fnmatch(origin, pattern):
                return True
    return False

# For Cloud Run deployment, we need to allow Cloud Run domains dynamically
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

# Add production origins from environment variable if available
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    production_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    allowed_origins.extend(production_origins)

# For Cloud Run, allow all .run.app domains (Google's Cloud Run domain pattern)
environment = os.getenv("ENVIRONMENT", "development")
if environment == "production":
    # Allow all Google Cloud Run domains
    allowed_origins.extend([
        "https://*.a.run.app",
        "https://*.run.app"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if environment != "production" else ["*"],
    allow_credentials=False if environment == "production" else True,  # Disable credentials with wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Import and include customer profile router
from api.customer_profile_api import export_router as customer_router
app.include_router(customer_router, prefix="/api")

# API routes should be defined before the catch-all route

# Mount static files (React build) if available
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "build")
if os.path.exists(static_dir):
    # Mount static files under /static
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")
    
    # Serve index.html for the root path
    @app.get("/")
    async def serve_frontend():
        """Serve React frontend"""
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "HOT Intelligent Travel Assistant API", "version": "1.0.0", "frontend": "not_built"}
    
    # Catch-all route for client-side routing - must be the last route
    @app.get("/{catch_all:path}")
    async def catch_all_routes(catch_all: str):
        """Catch all routes for React Router (SPA)"""
        # Don't intercept API routes or static files
        if any(catch_all.startswith(prefix) for prefix in [
            "api/", "travel/", "user/", "health", "database/", "customer/", "static/"
        ]):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Serve React app for all other routes
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend not found")
        raise HTTPException(status_code=404, detail="Frontend not available")

# Pydantic models for API

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
    itinerary: Optional[dict] = None
    session_info: Optional[SessionInfo]

class SendMailResponse(BaseModel):
    success: bool
    message: str
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

# Customer Profile Management endpoints
@app.get("/customer/profile/{email}")
async def get_customer_profile(email: str, db = Depends(get_db)):
    """
    Get customer profile with travel history and personalized suggestions
    """
    logger.info(f"🔍 DEBUG: Customer profile request for email: {email}")
    
    try:
        from services.customer_profile_service import CustomerProfileService
        
        logger.info(f"📦 DEBUG: Initializing CustomerProfileService")
        service = CustomerProfileService()
        
        logger.info(f"🔄 DEBUG: Generating personalized suggestions for: {email}")
        suggestions = service.generate_personalized_suggestions(db, email)
        
        logger.info(f"✅ DEBUG: Successfully generated suggestions")
        logger.info(f"📊 DEBUG: Response data keys: {list(suggestions.keys()) if suggestions else 'None'}")
        
        if suggestions:
            logger.info(f"📈 DEBUG: Suggestions count: {suggestions.get('suggestions', [])}")
            logger.info(f"👤 DEBUG: Customer name: {suggestions.get('customer_name', 'Unknown')}")
            logger.info(f"📧 DEBUG: Customer email: {suggestions.get('customer_email', 'Unknown')}")
            logger.info(f"🎯 DEBUG: Travel history count: {suggestions.get('travel_history_count', 0)}")
        
        response = {
            "success": True,
            "data": suggestions
        }
        logger.info(f"📤 DEBUG: Returning response with success=True")
        return response
        
    except Exception as e:
        logger.error(f"❌ DEBUG: Error getting customer profile for {email}", error=str(e))
        logger.error(f"🚨 DEBUG: Exception type: {type(e).__name__}")
        logger.error(f"🚨 DEBUG: Exception details: {str(e)}")
        
        # Import traceback for detailed error logging
        import traceback
        logger.error(f"🔍 DEBUG: Full traceback:\n{traceback.format_exc()}")
        
        response = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        logger.info(f"📤 DEBUG: Returning error response: {response}")
        return response

@app.post("/customer/profile")
async def create_customer_profile(customer_data: dict, db = Depends(get_db)):
    """
    Create or update customer profile
    """
    try:
        from services.customer_profile_service import CustomerProfileService
        
        service = CustomerProfileService()
        customer = service.get_or_create_customer(
            db, 
            customer_data.get("email"),
            customer_data.get("first_name"),
            customer_data.get("last_name")
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

@app.post("/customer/travel-history")
async def add_travel_history(history_data: dict, db = Depends(get_db)):
    """
    Add travel history for customer
    """
    try:
        from services.customer_profile_service import CustomerProfileService
        from datetime import datetime
        
        service = CustomerProfileService()
        
        # Convert date strings to date objects
        if 'travel_date_start' in history_data:
            history_data['travel_date_start'] = datetime.strptime(history_data['travel_date_start'], '%Y-%m-%d').date()
        if 'travel_date_end' in history_data:
            history_data['travel_date_end'] = datetime.strptime(history_data['travel_date_end'], '%Y-%m-%d').date()
        
        history = service.add_travel_history(db, history_data.get("email"), history_data)
        
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

# Cache management endpoints
@app.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics for demonstration purposes
    """
    try:
        from agents.cache.llm_cache import LLMCache
        cache = LLMCache()
        stats = cache.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        logger.error("Error getting cache stats", error=str(e))
        return {
            "success": False, 
            "error": str(e)
        }

@app.post("/cache/clear")
async def clear_all_cache():
    """
    Clear all cache files for demonstration purposes
    """
    try:
        from agents.cache.llm_cache import LLMCache
        cache = LLMCache()
        result = cache.clear_all_cache()
        return result
    except Exception as e:
        logger.error("Error clearing cache", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "files_removed": 0
        }

@app.post("/cache/cleanup")
async def cleanup_expired_cache():
    """
    Clean up only expired cache files
    """
    try:
        from agents.cache.llm_cache import LLMCache
        cache = LLMCache()
        removed_count = cache.clear_expired_cache()
        return {
            "success": True,
            "expired_files_removed": removed_count,
            "message": f"Removed {removed_count} expired cache files"
        }
    except Exception as e:
        logger.error("Error cleaning up cache", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "expired_files_removed": 0
        }

@app.post("/travel/sendmail", response_model=SendMailResponse)
async def sendmail(email_data: EmailData):
    try:
        # Check Gmail status for user feedback
        gmail_enabled = os.getenv("GMAIL_ENABLED", "false").lower() == "true"
        
        print(f"📧 Email request received for: {email_data.customer.email}")
        print(f"🔧 Gmail status: {'Enabled' if gmail_enabled else 'Demo mode (disabled)'}")
        
        # Debug: Print email data structure
        print(f"📧 Email data - Customer: {email_data.customer.name}")
        print(f"📧 Email data - Destination: {email_data.trip_details.destination}")
        
        # Send email (real or simulated based on GMAIL_ENABLED)
        result = send_message(email_data)
        print(f"📧 Send message result: {result}")
        
        # Return appropriate success message
        if gmail_enabled:
            return {"success": True, "message": "✅ Email sent successfully"}
        else:
            return {"success": True, "message": "✅ Email simulated successfully (Gmail disabled - demo mode)"}
            
    except Exception as e:
        gmail_enabled = os.getenv("GMAIL_ENABLED", "false").lower() == "true"
        error_context = "Gmail enabled" if gmail_enabled else "Demo mode"
        raise HTTPException(status_code=500, detail=f"❌ Failed to send email ({error_context}): {str(e)}")

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