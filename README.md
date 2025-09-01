# HOT Intelligent Travel Assistant - Beginner's Guide

## 🌍 What is this application?

The HOT Intelligent Travel Assistant is an AI-powered travel planning application that helps you:
- Plan complete travel itineraries
- Get visa and travel requirement information
- Find flights, hotels, and travel deals
- Receive personalized travel recommendations
- Access House of Travel (HOT) specific services

## 🏗️ Application Architecture

This application consists of three main components:
1. **Frontend (React)** - The user interface you interact with
2. **Backend (FastAPI)** - The AI-powered server that processes requests
3. **Database (SQLite)** - Lightweight database that requires zero configuration

## 📋 Prerequisites (What you need installed)

**Minimal setup for MVP** - Only need these 2 things:

### 1. Python (3.10 or higher)
- **Mac**: Install via [Homebrew](https://brew.sh/) with `brew install python`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Linux**: Use your package manager (e.g., `sudo apt install python3`)

### 2. Node.js (16 or higher)
- Download from [nodejs.org](https://nodejs.org/)
- This includes npm (Node Package Manager)

### 3. Git (optional but recommended)
- Download from [git-scm.com](https://git-scm.com/downloads)

**That's it!** No database server installation needed - SQLite is built into Python!

## ⚡ Super Quick Setup (3 commands!)

```bash
# 1. Clone and navigate
git clone <repo-url> && cd hot_intelligent_travel_assistant

# 2. Setup everything automatically
bash setup.sh

# 3. Start the application
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Done!** Open http://localhost:8000 in your browser! 🎉

---

## 🚀 Detailed Setup Guide

### Step 1: Download the Project

If you have the project files already, skip to Step 2. If not:

```bash
# If using git
git clone <repository-url>
cd hot_intelligent_travel_assistant

# Or download and extract the ZIP file, then navigate to the folder
```

### Step 2: Set Up Environment Variables

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your API keys:
```bash
# Required: Add your Google Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Add Amadeus API credentials for flight/hotel search
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
```

**How to get API keys:**
- **Gemini API Key**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Amadeus API**: Sign up at [developers.amadeus.com](https://developers.amadeus.com/)

### Step 3: Start the Database

The application uses MySQL database running in a container:

```bash
# Start Podman machine (Mac/Windows only)
podman machine start

# Start MySQL database
podman-compose up mysql -d

# Wait 10-15 seconds for database to fully start
```

**Troubleshooting:**
- If `podman-compose` doesn't work, try `docker-compose`
- If you get permission errors, try adding `sudo` before commands (Linux)

### Step 4: Set Up Python Backend

1. **Create a virtual environment** (recommended):
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

2. **Install Python dependencies**:
```bash
pip install -r requirements-core.txt
```

3. **Set up the database**:
```bash
python -c "from config.database import engine; from models.database_models import Base; Base.metadata.create_all(bind=engine)"
```

4. **Start the backend server**:
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 5: Set Up React Frontend

Open a **new terminal window** and navigate to the project folder:

```bash
cd hot_intelligent_travel_assistant/frontend

# Install frontend dependencies
npm install

# Start the frontend server
npm start
```

You should see:
```
Local:            http://localhost:3000
```

## 🎯 Access the Application

Once both servers are running:

1. **Frontend (User Interface)**: http://localhost:3000
2. **Backend API Documentation**: http://localhost:8000/docs
3. **API Health Check**: http://localhost:8000/health

## 💬 How to Use the Application

1. **Open your browser** and go to http://localhost:3000
2. **Optional**: Enter your nationality for personalized recommendations
3. **Start chatting** with the AI assistant:
   - "Plan a 7-day trip to Japan for 2 people"
   - "What visa do I need for Thailand?"
   - "Find cheap flights to Europe"
   - "What vaccinations do I need for India?"

## 🛠️ Common Issues and Solutions

### Issue: "Connection refused" or API errors
**Solution**: Make sure the backend server is running on port 8000
```bash
# Check if backend is running
curl http://localhost:8000/health
```

### Issue: Frontend won't start
**Solution**: 
1. Make sure Node.js is installed: `node --version`
2. Delete node_modules and reinstall: `rm -rf node_modules && npm install`

### Issue: Database connection errors
**Solution**:
1. Check if MySQL container is running: `podman ps`
2. Restart the database: `podman-compose restart mysql`
3. Wait 15-30 seconds before testing again

### Issue: "Module not found" errors in Python
**Solution**: 
1. Make sure your virtual environment is activated
2. Reinstall requirements: `pip install -r requirements-core.txt`

### Issue: Podman machine not starting (Mac/Windows)
**Solution**:
```bash
# Initialize and start Podman machine
podman machine init
podman machine start
```

## 📁 Project Structure

```
hot_intelligent_travel_assistant/
├── api/                    # FastAPI backend
│   └── main.py            # Main API endpoints
├── frontend/              # React frontend
│   ├── src/
│   │   ├── App.js         # Main React component
│   │   └── index.css      # Styling
│   └── package.json       # Frontend dependencies
├── agents/                # AI agents
├── config/                # Database configuration
├── models/                # Database models
├── orchestrator/          # Agent orchestration
├── .env                   # Environment variables
├── requirements-core.txt  # Python dependencies
└── podman-compose.yml     # Database container config
```

## 🔧 Development Tips

### Stopping the Application
- **Frontend**: Press `Ctrl+C` in the frontend terminal
- **Backend**: Press `Ctrl+C` in the backend terminal
- **Database**: `podman-compose down`

### Viewing Logs
- **Backend**: Logs appear in the terminal where you ran `uvicorn`
- **Database**: `podman-compose logs mysql`

### Restarting Components
```bash
# Restart backend (if you made code changes)
# Just press Ctrl+C and run uvicorn command again

# Restart frontend
# Press Ctrl+C and run npm start again

# Restart database
podman-compose restart mysql
```

## 🌟 Features Overview

### Chat Interface
- Clean, modern messaging UI
- Suggestion bubbles for common queries
- Loading indicators during processing
- Error handling with helpful messages

### Travel Planning
- Multi-agent AI system for comprehensive planning
- Visa and travel requirement analysis
- Flight and hotel search integration (with Amadeus API)
- Personalized recommendations based on user profile

### Database Features
- User profile storage
- Travel history tracking
- Search session management
- Commercial knowledge base for HOT-specific deals

## 📞 Getting Help

If you encounter issues:

1. **Check the logs** in your terminal windows
2. **Verify all services are running**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000/health
   - Database: `podman ps` should show MySQL container
3. **Review this README** for common solutions
4. **Check environment variables** in `.env` file

## 🎉 Success!

If you can access http://localhost:3000 and chat with the AI assistant, congratulations! You've successfully set up and run the HOT Intelligent Travel Assistant.

---

**Note**: This application is designed for development and testing. For production deployment, additional security and performance configurations would be needed.