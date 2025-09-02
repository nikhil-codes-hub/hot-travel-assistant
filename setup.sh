#!/bin/bash

echo "🚀 Setting up HOT Travel Assistant MVP (SQLite - Zero Configuration!)"

# Check if we're in a conda environment
if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "⚠️  Warning: No conda environment detected. Please run 'conda activate your_environment_name' first"
    exit 1
fi

echo "✅ Using conda environment: $CONDA_DEFAULT_ENV"

# Install dependencies - now the main requirements.txt works without MySQL!
python -m venv hotenv
source hotenv/bin/activate
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file for SQLite
if [[ ! -f .env ]]; then
    echo "📝 Creating .env file for SQLite..."
    cat > .env << EOF
# Database Configuration (SQLite - no MySQL needed)
DATABASE_URL=sqlite:///./hot_travel_assistant.db

# AI Configuration - Add your keys here
GEMINI_API_KEY=your_gemini_api_key_here
# OR use Vertex AI
GOOGLE_CLOUD_PROJECT=your_project_id
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# API Integrations
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret

# Environment
ENVIRONMENT=development
AI_PROVIDER=vertex
EOF
    echo "✅ Created .env file"
else
    echo "ℹ️  .env file already exists"
fi

# Create the SQLite database
echo "🗄️  Creating SQLite database..."
python -c "
from config.database import engine
from models.database_models import Base
Base.metadata.create_all(bind=engine)
print('✅ Database created successfully')
"

echo ""
echo "🎉 Setup complete! You can now run:"
echo "   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📁 Database: SQLite (./hot_travel_assistant.db)"
echo "🌐 API: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"