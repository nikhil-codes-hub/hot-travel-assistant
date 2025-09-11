#!/bin/bash

# Full-stack deployment script for HOT Travel Assistant
# Automatically handles backend and frontend deployment with URL synchronization

set -e  # Exit on any error

echo "🚀 Starting full-stack deployment..."

# Step 1: Deploy backend
echo "📦 Deploying backend to Cloud Run..."
gcloud run deploy hot-travel-backend \
  --source . \
  --allow-unauthenticated \
  --port 8080 \
  --region us-central1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=ace-agility-304513,VERTEX_AI_LOCATION=us-central1,AMADEUS_CLIENT_ID=DHdjRGkND0GefDhGAAbO7Gn5lr3EgG3P,AMADEUS_CLIENT_SECRET=x91XH0FoAqeBEV5h,ENVIRONMENT=production,AI_PROVIDER=vertex,LLM_CACHE_DIR=cache/llm_responses,LLM_CACHE_DURATION_HOURS=24"

# Step 2: Get the backend URL automatically
echo "🔍 Getting backend URL..."
BACKEND_URL=$(gcloud run services describe hot-travel-backend --region us-central1 --format="value(status.url)")
echo "✅ Backend deployed at: $BACKEND_URL"

# Step 3: Deploy frontend with backend URL
echo "🖥️  Deploying frontend with backend URL..."
cd frontend
gcloud run deploy hot-travel-frontend \
  --source . \
  --allow-unauthenticated \
  --region us-central1 \
  --set-env-vars "REACT_APP_API_URL=$BACKEND_URL"

# Step 4: Get frontend URL
FRONTEND_URL=$(gcloud run services describe hot-travel-frontend --region us-central1 --format="value(status.url)")
echo "✅ Frontend deployed at: $FRONTEND_URL"

echo ""
echo "🎉 Deployment Complete!"
echo "===================================="
echo "🖥️  Frontend: $FRONTEND_URL"
echo "⚙️  Backend:  $BACKEND_URL"
echo "===================================="
echo ""
echo "🔧 System Features:"
echo "  ✅ Interactive travel chatbot"
echo "  ✅ Multi-agent AI system"  
echo "  ✅ Smart caching (24-hour duration)"
echo "  ✅ Cache management panel"
echo "  ✅ Professional House of Travel UI"
echo "  ✅ Vertex AI integration"
echo "  ✅ Amadeus API integration"
echo ""
echo "🎯 Ready for jury demonstration!"