#!/bin/bash

# HOT Travel Assistant Startup Script
echo "🚀 Starting HOT Travel Assistant..."

# Check if database exists, if not initialize it
if [ ! -f "hot_travel_assistant.db" ]; then
    echo "📦 Initializing database with sample data..."
    python database/sample_customer_data.py
fi

# Start backend server in the background
echo "🔧 Starting backend API server on port 8000..."
python -m uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Give backend time to start
sleep 3

# Start frontend in the background
echo "🎨 Starting frontend on port 3000..."
cd frontend && npm start &
FRONTEND_PID=$!

echo ""
echo "✅ HOT Travel Assistant is running!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📧 Test customer emails:"
echo "  • henry.thomas596@yahoo.com"
echo "  • john.doe@example.com"
echo "  • jane.smith@example.com"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for Ctrl+C
trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait