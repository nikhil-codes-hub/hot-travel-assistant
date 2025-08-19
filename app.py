"""
HOT Travel Assistant - Visa Requirements Service
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import logging
import os
from dotenv import load_dotenv

# Import orchestrator for agent coordination
from orchestrator import orchestrator

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HOT Travel Assistant", version="1.0.0")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")

# Mount React build directory for production
import os
if os.path.exists("build"):
    app.mount("/static", StaticFiles(directory="build/static"), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def react_app(request: Request):
        """Serve React app."""
        with open("build/index.html", "r") as f:
            return HTMLResponse(content=f.read())
else:
    # Fallback to original template for development
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Serve the main page."""
        return templates.TemplateResponse("index.html", {"request": request})


# Agent orchestration is now handled by the orchestrator module

class VisaQuery(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"

class TravelQuery(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"

class TravelResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    agent_type: str = "Unknown"
    confidence: float = 1.0

# Legacy compatibility - keep VisaResponse for now
VisaResponse = TravelResponse


@app.post("/chat", response_model=TravelResponse)
async def chat(query: TravelQuery):
    """Process travel queries using agent orchestration."""
    logger.info(f"Query: {query.message}")
    
    try:
        # Use orchestrator to handle the query
        agent_response = await orchestrator.process_query(query.message, query.user_id)
        
        # Convert AgentResponse to TravelResponse
        return TravelResponse(
            response=agent_response.response,
            suggestions=agent_response.suggestions,
            agent_type=agent_response.agent_type,
            confidence=agent_response.confidence
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return TravelResponse(
            response="Sorry, I encountered an error processing your request. Please try again.",
            suggestions=["Try a different question", "Ask about visa requirements"],
            agent_type="Error",
            confidence=0.0
        )

@app.get("/health")
async def health():
    """Health check with all service statuses."""
    orchestrator_info = orchestrator.get_agent_info()
    
    return {
        "status": "healthy", 
        "service": "HOT Travel Assistant",
        "architecture": "Multi-Agent with LangGraph Orchestration",
        "orchestrator": orchestrator_info["orchestrator"],
        "agents": orchestrator_info["agents"],
        "capabilities": {
            "visa_requirements": "Active",
            "multi_agent_support": "Ready for expansion",
            "langgraph_coordination": "Enabled"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🌍 HOT Travel Assistant")
    print("=" * 40)
    print("✅ Multi-Agent Travel Assistance Platform")
    print("🔗 LangGraph Orchestration with React Frontend")
    print()
    
    # Get orchestrator status
    orchestrator_info = orchestrator.get_agent_info()
    print("🤖 Agent Architecture:")
    print(f"   Orchestrator: {'✅ ACTIVE' if orchestrator_info['orchestrator']['graph_compiled'] else '❌ DEGRADED'}")
    print(f"   Available Agents: {orchestrator_info['orchestrator']['total_agents']}")
    
    for agent_name, agent_info in orchestrator_info['agents'].items():
        if 'error' not in agent_info:
            print(f"   • {agent_name.title()}: ✅ {agent_info.get('description', 'Ready')}")
        else:
            print(f"   • {agent_name.title()}: ❌ {agent_info['error']}")
    
    print()
    print("🚀 Ready for team collaboration!")
    print("📋 Framework: Add new agents in agents/ directory")
    print("📱 Frontend: React build served automatically")
    print("📱 Open: http://localhost:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)