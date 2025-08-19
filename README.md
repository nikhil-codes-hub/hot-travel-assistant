# HOT Travel Assistant

Intelligent visa requirements service with React frontend and FastAPI backend, featuring optional Google Vertex AI integration.

## 🚀 Quick Start

### Frontend (React)
```bash
# Install React dependencies
npm install

# Development mode (hot reload)
npm start  # Runs on http://localhost:3000

# Production build
npm run build
```

### Backend (FastAPI)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run FastAPI server
python app.py  # Runs on http://localhost:8003
```

### Full Application
1. Build React frontend: `npm run build`
2. Start FastAPI: `python app.py`
3. Open: http://localhost:8003

### Optional: AI Mode (Requires GCP Setup)
```bash
# Configure Vertex AI (if authorized)
cp .env.example .env
# Edit .env and set GOOGLE_CLOUD_PROJECT=your-project-id
# Authenticate with: gcloud auth application-default login
```

⚠️ **Note**: GCP configuration should only be done by authorized personnel following company policies.

## 🤖 AI vs Fallback Mode

### AI Mode (Vertex AI Connected)
- ✅ **Dynamic responses** using Google's Gemini model
- ✅ **Intelligent analysis** of complex visa questions
- ✅ **Up-to-date information** based on AI training
- ✅ **Natural conversation** with context understanding

### Fallback Mode (No AI)
- 📋 **Static responses** from hardcoded data
- 📋 **Limited to** Japan, China, India, Schengen
- 📋 **Basic pattern matching** for country detection

## 📁 Project Structure
```
hot_travel_assistant/
├── src/                    # React frontend source
│   ├── App.js             # Main React component
│   ├── index.js           # React entry point
│   └── index.css          # Styles
├── public/                # React public assets
│   └── index.html         # HTML template
├── agents/                # Travel agent modules
│   ├── __init__.py        # Agent package initialization
│   ├── base_agent.py      # Base class for all agents
│   └── visa_agent.py      # Visa requirements specialist
├── templates/             # FastAPI templates (fallback)
│   └── index.html         # Original vanilla HTML
├── build/                 # React production build (after npm run build)
├── app.py                 # FastAPI backend with orchestration
├── orchestrator.py        # LangGraph agent coordination
├── requirements.txt       # Python dependencies (includes LangGraph)
├── package.json           # React dependencies
└── .env                   # Environment configuration
```

## 📁 Key Files for Development

### Frontend Components
- `src/App.js` - Main chat interface component
- `src/index.css` - Global styles and responsive design
- `src/index.js` - React entry point

### Agent System
- `agents/base_agent.py` - Base class that all agents must inherit from
- `agents/visa_agent.py` - Visa requirements specialist (example implementation)
- `orchestrator.py` - LangGraph workflow for agent coordination
- `app.py` - FastAPI application with agent integration

### Configuration
- `package.json` - React dependencies and scripts
- `requirements.txt` - Python dependencies (including LangGraph)
- `.env` - Environment variables (create from .env.example)

## 🔧 Features
- **React Frontend**: Modern, component-based UI with state management
- **FastAPI Backend**: High-performance async Python API
- **Dual Serving**: Serves React build in production, template fallback in development
- **Production Ready**: Fully functional fallback mode with comprehensive visa data
- **Responsive Design**: Perfect experience on all devices
- **Real-time Chat**: Interactive visa assistance with suggestions
- **Dual Mode Support**: Fallback mode + optional AI integration
- **Company Policy Compliant**: No unauthorized GCP testing
- **Health Monitoring**: Service status and mode indicators