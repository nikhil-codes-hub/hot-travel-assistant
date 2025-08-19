# Google Agent Engine Deployment Guide

## 🎯 Overview
This guide covers deploying the HOT Travel Assistant multi-agent platform to Google Agent Engine. The current FastAPI + LangGraph + React setup is compatible with Agent Engine deployment with some modifications.

## ✅ Current Compatibility Status

### **What's Already Compatible**
- ✅ **Python FastAPI backend** - Agent Engine supports Python
- ✅ **LangGraph orchestration** - Native Agent Engine integration
- ✅ **Multi-agent architecture** - Perfect for Agent Engine
- ✅ **Modular agent structure** - Agents in separate classes
- ✅ **BaseAgent interface** - Consistent agent contract

### **What Needs Modification**
- 🔧 Deployment configuration for Agent Engine
- 🔧 Requirements file updates
- 🔧 Environment variable handling
- 🔧 FastAPI integration with Agent Engine ADK

## 📋 Prerequisites

### **Google Cloud Setup**
1. **GCP Project** with billing enabled
2. **Vertex AI API** enabled
3. **Agent Engine API** enabled
4. **Required IAM permissions**:
   - `aiplatform.agents.create`
   - `aiplatform.agents.deploy`
   - `storage.objects.create` (for deployment artifacts)

### **Development Environment**
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
gcloud init

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

## 🔧 Required Code Changes

### 1. **Update Requirements File**
```python
# requirements.txt - Add Agent Engine dependencies
fastapi
uvicorn[standard]
pydantic
python-dotenv
aiohttp
langgraph>=0.0.69
langchain>=0.1.0
langchain-core>=0.1.0

# Agent Engine specific
google-cloud-aiplatform[agent_engines,langgraph]>=1.43.0
cloudpickle==3.0
google-adk-python

# Optional: Keep existing Vertex AI deps
vertexai>=1.69.0
google-auth>=2.23.4
```

### 2. **Create Agent Engine Deployment Script**
```python
# deploy_agent_engine.py
import os
from google.cloud import aiplatform
from google import agent_engines
from orchestrator import orchestrator

def deploy_to_agent_engine():
    """Deploy HOT Travel Assistant to Google Agent Engine"""
    
    # Initialize AI Platform
    aiplatform.init(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("VERTEX_AI_LOCATION", "us-central1")
    )
    
    # Define deployment requirements
    requirements = [
        "fastapi",
        "uvicorn[standard]", 
        "langgraph>=0.0.69",
        "langchain>=0.1.0",
        "langchain-core>=0.1.0",
        "google-cloud-aiplatform[agent_engines,langgraph]>=1.43.0",
        "cloudpickle==3.0",
        "pydantic",
        "python-dotenv",
        "aiohttp"
    ]
    
    # Environment variables for deployment
    env_vars = {
        "VERTEX_AI_LOCATION": os.getenv("VERTEX_AI_LOCATION", "us-central1"),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        # Note: GOOGLE_CLOUD_PROJECT is auto-configured in Agent Engine
    }
    
    print("🚀 Deploying HOT Travel Assistant to Agent Engine...")
    
    try:
        # Deploy the orchestrator as the main agent
        remote_agent = agent_engines.create(
            local_agent=orchestrator,
            requirements=requirements,
            env_vars=env_vars,
            display_name="HOT Travel Assistant",
            description="Multi-agent travel assistance platform with visa, flight, and travel planning capabilities",
            # Optional: Specify machine type
            # machine_type="n1-standard-2"
        )
        
        print(f"✅ Agent deployed successfully!")
        print(f"Agent ID: {remote_agent.name}")
        print(f"Endpoint: {remote_agent.resource_name}")
        
        return remote_agent
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return None

if __name__ == "__main__":
    deploy_to_agent_engine()
```

### 3. **Modify Orchestrator for Agent Engine Compatibility**
```python
# Add to orchestrator.py
from google.adk.cli.fast_api import get_fast_api_app

class TravelOrchestrator:
    # ... existing code ...
    
    def get_agent_engine_app(self):
        """Get FastAPI app configured for Agent Engine deployment"""
        try:
            # Use Agent Engine's FastAPI integration
            return get_fast_api_app(
                agents_dir="agents/",
                allow_origins=["*"],  # Configure as needed
                web=True,  # Enable web interface
                session_service_uri=None  # Use default
            )
        except ImportError:
            # Fallback to regular FastAPI app
            from app import app
            return app
    
    def get_deployment_info(self) -> Dict[str, Any]:
        """Get deployment information for Agent Engine"""
        return {
            "platform": "Google Agent Engine",
            "agents": list(self.agents.keys()),
            "capabilities": [
                cap for agent in self.agents.values() 
                for cap in agent.get_capabilities()
            ],
            "orchestration": "LangGraph",
            "status": "ready_for_deployment"
        }

# Add Agent Engine app getter
def get_agent_engine_app():
    """Entry point for Agent Engine deployment"""
    return orchestrator.get_agent_engine_app()
```

### 4. **Update App.py for Agent Engine**
```python
# Add to app.py after existing imports
try:
    from google.adk.cli.fast_api import get_fast_api_app
    AGENT_ENGINE_AVAILABLE = True
except ImportError:
    AGENT_ENGINE_AVAILABLE = False

# Add new endpoint for Agent Engine compatibility
@app.get("/agent-engine/health")
async def agent_engine_health():
    """Health check specific for Agent Engine deployment"""
    orchestrator_info = orchestrator.get_agent_info()
    
    return {
        "status": "healthy",
        "platform": "Agent Engine Ready",
        "service": "HOT Travel Assistant",
        "deployment_target": "Google Agent Engine",
        "agent_engine_available": AGENT_ENGINE_AVAILABLE,
        "orchestrator": orchestrator_info["orchestrator"],
        "agents": orchestrator_info["agents"],
        "deployment_info": orchestrator.get_deployment_info() if hasattr(orchestrator, 'get_deployment_info') else {}
    }

# Entry point for Agent Engine
def create_agent_engine_app():
    """Create app instance for Agent Engine deployment"""
    if AGENT_ENGINE_AVAILABLE:
        return orchestrator.get_agent_engine_app()
    else:
        return app
```

## 🚀 Deployment Options

### **Option 1: Full Agent Engine Deployment** ⭐ Recommended for AI Features

#### **Pros:**
- Native LangGraph integration
- Built-in agent management
- Automatic scaling
- Integrated monitoring
- AI-first platform

#### **Cons:**  
- Requires GCP access (company policy consideration)
- Different architecture from current setup
- React frontend needs separate deployment

#### **Steps:**
```bash
# 1. Prepare deployment
python deploy_agent_engine.py

# 2. Deploy React frontend separately (Cloud Run)
npm run build
gcloud run deploy hot-travel-frontend --source .

# 3. Configure CORS for cross-origin requests
```

### **Option 2: Hybrid Deployment**

#### **Architecture:**
- Agent Engine: Orchestrator + Agents
- Cloud Run: React Frontend + API Gateway  
- Communication: REST API between services

#### **Pros:**
- Best of both worlds
- Keep current frontend architecture
- Agent Engine benefits for AI

#### **Cons:**
- More complex setup
- Multiple services to manage
- Higher latency

### **Option 3: Cloud Run Deployment** (Easier Migration)

#### **Pros:**
- Minimal code changes
- Keep current architecture
- Company policy friendly
- Single service deployment

#### **Cons:**
- No Agent Engine specific features
- Manual scaling management
- Less AI-optimized

#### **Steps:**
```bash
# Simple Cloud Run deployment
gcloud run deploy hot-travel-assistant --source .
```

## 🔧 Configuration Files

### **Agent Engine Deployment Config**
```yaml
# agent_engine_config.yaml
name: "hot-travel-assistant"
display_name: "HOT Travel Assistant"
description: "Multi-agent travel assistance platform"

runtime:
  python_version: "3.9"
  
requirements:
  - "fastapi"
  - "langgraph>=0.0.69"
  - "google-cloud-aiplatform[agent_engines,langgraph]>=1.43.0"
  
environment:
  VERTEX_AI_LOCATION: "us-central1"
  GEMINI_MODEL: "gemini-1.5-flash"
  
resources:
  cpu: "1"
  memory: "2Gi"
  
scaling:
  min_instances: 0
  max_instances: 10
```

### **Docker Configuration** (for Cloud Run alternative)
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install Node.js for React build
RUN apt-get update && apt-get install -y nodejs npm
RUN npm install && npm run build

# Expose port
EXPOSE 8080

# Set environment variable for Cloud Run
ENV PORT=8080

# Start command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## 🚨 Important Considerations

### **Company Policy Compliance**
- **GCP Access**: Agent Engine deployment requires GCP access
- **Data Residency**: Ensure compliance with data location requirements  
- **Security**: Review Agent Engine security model
- **Billing**: Understand Agent Engine pricing model

### **Technical Limitations**
- **React Frontend**: Agent Engine typically provides its own interface
- **Static Assets**: May need separate CDN/hosting for React build
- **Custom Endpoints**: Some FastAPI endpoints may need modification
- **Session Management**: Agent Engine handles sessions differently

### **Migration Strategy**
1. **Phase 1**: Deploy to Cloud Run (minimal changes)
2. **Phase 2**: Extract agents to Agent Engine (hybrid)
3. **Phase 3**: Full Agent Engine migration (if beneficial)

## 📊 Deployment Comparison

| Feature | Agent Engine | Cloud Run | Hybrid |
|---------|-------------|-----------|---------|
| **Setup Complexity** | Medium | Low | High |
| **AI Features** | Excellent | Good | Excellent |
| **Scaling** | Automatic | Manual/Auto | Mixed |
| **Cost** | Variable | Predictable | Higher |
| **Company Policy** | ⚠️ Review | ✅ Safe | ⚠️ Review |
| **Maintenance** | Low | Medium | High |

## 🔍 Testing Deployment

### **Local Testing**
```bash
# Test Agent Engine compatibility
python -c "
from orchestrator import orchestrator
from google.adk.cli.fast_api import get_fast_api_app
print('Agent Engine compatibility:', 'OK')
"

# Test deployment script
python deploy_agent_engine.py --dry-run
```

### **Health Checks**
```bash
# Agent Engine health
curl https://your-agent-endpoint/health

# Agent Engine specific health  
curl https://your-agent-endpoint/agent-engine/health
```

## 📋 Deployment Checklist

### **Pre-Deployment**
- [ ] GCP project setup with billing
- [ ] APIs enabled (Vertex AI, Agent Engine)
- [ ] IAM permissions configured
- [ ] Company policy approval (if required)
- [ ] Environment variables configured
- [ ] Requirements file updated

### **Deployment**
- [ ] Agent Engine deployment script tested
- [ ] Orchestrator compatibility verified
- [ ] Agent registration working
- [ ] Health endpoints responding
- [ ] Error handling tested

### **Post-Deployment**
- [ ] Agent Engine endpoint accessible
- [ ] All agents responding correctly
- [ ] LangGraph workflow functioning
- [ ] Performance monitoring setup
- [ ] Logging configuration verified

## 🆘 Troubleshooting

### **Common Issues**

#### **"Package not found" during deployment**
```bash
# Solution: Pin package versions in requirements.txt
langgraph==0.0.69
langchain==0.1.0
```

#### **"Agent Engine API not enabled"**
```bash
# Solution: Enable the API
gcloud services enable aiplatform.googleapis.com
```

#### **"Permission denied" errors**
```bash
# Solution: Add required IAM roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/aiplatform.user"
```

#### **"Import error for google.adk"**
```bash
# Solution: Install Agent Development Kit
pip install google-adk-python
```

### **Debugging Commands**
```bash
# Check deployment status
gcloud ai agents list

# View agent logs
gcloud ai agents describe AGENT_ID

# Test agent endpoint
curl -X POST https://AGENT_ENDPOINT/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Do I need a visa for Japan?"}'
```

## 📚 Resources

### **Google Cloud Documentation**
- [Agent Engine Overview](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine)
- [Agent Engine Deployment](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy)
- [LangGraph Integration](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/langgraph)

### **Development Resources**
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Cloud Run Python Quickstart](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)

---

## 🎯 Recommendation

**For HOT Hackathon**: Start with **Cloud Run deployment** for immediate deployment and team collaboration, then consider **Agent Engine migration** if AI features and automatic scaling become priorities and company policies allow GCP integration.

**Next Steps**: 
1. Review company policies regarding GCP deployment
2. Choose deployment option based on requirements
3. Test deployment in staging environment
4. Plan migration strategy if moving from Cloud Run to Agent Engine later