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

### 4. Podman (optional - for containerized deployment)
- **Mac**: Install via [Homebrew](https://brew.sh/) with `brew install podman`
- **Windows**: Download from [podman.io](https://podman.io/getting-started/installation#windows)
- **Linux**: Use your package manager:
  - **Ubuntu/Debian**: `sudo apt install podman`
  - **RHEL/CentOS**: `sudo dnf install podman`
  - **Arch**: `sudo pacman -S podman`

**Note**: Podman is only needed if you want to run the application in containers. The SQLite version runs natively without any containerization.

**That's it for basic setup!** No database server installation needed - SQLite is built into Python!

## ⚡ Super Quick Setup (4 commands!)

```bash
# 1. Clone and navigate
git clone <repo-url> && cd hot_intelligent_travel_assistant

# 2. Setup everything automatically
bash setup.sh

# 3. Start the backend (in first terminal)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Start the frontend (in second terminal)
# Open new terminal, navigate to project, then:
cd frontend && npm install && npm start
```

**Done!** Open http://localhost:3000 for the travel assistant UI! 🎉
- **Frontend (Travel Assistant)**: http://localhost:3000
- **Backend API**: http://localhost:8000

---

## 🚀 Detailed Setup Guide

> **💡 Prefer the 3-command setup above?** The detailed steps below are the same as `bash setup.sh` but broken down step-by-step for learning purposes.

### Step 1: Download the Project

If you have the project files already, skip to Step 2. If not:

```bash
# If using git
git clone <repository-url>
cd hot_intelligent_travel_assistant

# Or download and extract the ZIP file, then navigate to the folder
```

### Step 2: Create Python Environment

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

### Step 3: Install Dependencies

```bash
# Install all Python dependencies
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables (Optional)

The application works without any API keys, but for full functionality:

1. Create a `.env` file:
```bash
# Optional: Add your AI API keys for enhanced features
GEMINI_API_KEY=your_gemini_api_key_here
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
```

**How to get API keys:**
- **Gemini API Key**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Amadeus API**: Sign up at [developers.amadeus.com](https://developers.amadeus.com/)

**Note**: Without API keys, the system uses fallback parsing and shows demo data.

### Step 5: Initialize Database

The SQLite database is created automatically, but you can initialize it explicitly:

```bash
python -c "from config.database import engine; from models.database_models import Base; Base.metadata.create_all(bind=engine)"
```

### Step 6: Start the Backend Server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🗄️  Using SQLite database (perfect for MVP!)
📁 Database: sqlite:///./hot_travel_assistant.db
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 7: Set Up React Frontend

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
1. Check if SQLite database file exists: `ls -la hot_travel_assistant.db`
2. Try reinitializing: `python -c "from config.database import engine; from models.database_models import Base; Base.metadata.create_all(bind=engine)"`
3. Restart the backend server

### Issue: "Module not found" errors in Python
**Solution**: 
1. Make sure your virtual environment is activated
2. Reinstall requirements: `pip install -r requirements.txt`

### Issue: SQLite database locked
**Solution**:
1. Close any other instances of the application
2. Delete `hot_travel_assistant.db` file and restart (database will be recreated)

### Issue: Frontend not connecting to backend
**Solution**:
1. Make sure backend is running on port 8000: `curl http://localhost:8000/health`
2. Check if frontend is pointing to correct API URL in the code

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
├── requirements.txt       # Python dependencies
├── setup.sh              # Automated setup script
├── hot_travel_assistant.db # SQLite database (created automatically)
└── podman-compose.yml     # Optional: container config
```

## 🔧 Development Tips

### Stopping the Application
- **Frontend**: Press `Ctrl+C` in the frontend terminal
- **Backend**: Press `Ctrl+C` in the backend terminal
- **Database**: SQLite stops automatically when backend stops

### Viewing Logs
- **Backend**: Logs appear in the terminal where you ran `uvicorn`
- **Database**: SQLite operations are logged in the backend terminal

### Restarting Components
```bash
# Restart backend (if you made code changes)
# Just press Ctrl+C and run uvicorn command again

# Restart frontend
# Press Ctrl+C and run npm start again

# Database restarts automatically with backend (SQLite)
```

---

## 🐳 Optional: Containerized Deployment with Podman

If you installed Podman and want to run the application in containers:

### Setting up Podman Machine (Mac/Windows only)
```bash
# Initialize Podman machine
podman machine init

# Start Podman machine
podman machine start

# Verify Podman is working
podman run hello-world
```

### Using Podman with the Application
```bash
# Build application container (if Dockerfile exists)
podman build -t hot-travel-assistant .

# Run with container networking
podman run -p 8000:8000 -p 3000:3000 hot-travel-assistant
```

**Note**: The SQLite version works great without containers. Containerization is optional for production deployments.

## 🐛 Troubleshooting

### Database Column Length Errors

If you see errors like `"Data too long for column 'nationality'"` when using MySQL:

```bash
# Run the database migration script
python migrate_database.py
```

This will automatically:
- Check your current database schema
- Extend varchar columns that are too short
- Fix nationality column length issues
- Ensure compatibility with user profile data

**Requirements for migration:**
- MySQL database with existing user_profiles table
- DATABASE_URL set in .env file
- Database user with ALTER privileges

### Common Issues

1. **"Repository not found" when cloning:**
   - Repository might be private - ensure you have access
   - Use SSH instead: `git clone git@github.com:nikhil-codes-hub/hot-travel-assistant.git`
   - Check your GitHub authentication

2. **MySQL connection errors:**
   - Make sure MySQL is running
   - Verify DATABASE_URL in .env file
   - Check database credentials and permissions

3. **Frontend build errors:**
   - Delete node_modules: `rm -rf frontend/node_modules`
   - Clear npm cache: `npm cache clean --force`  
   - Reinstall: `cd frontend && npm install`

4. **API authentication errors:**
   - Check AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env
   - Verify GOOGLE_CLOUD_PROJECT and VERTEX_AI_LOCATION for Vertex AI
   - Ensure proper IAM permissions for Vertex AI usage

---

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