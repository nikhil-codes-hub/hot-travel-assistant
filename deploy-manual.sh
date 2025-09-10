#!/bin/bash

# Manual deployment script for HOT Travel Assistant
set -e

PROJECT_ID="ace-agility-304513"
SERVICE_NAME="hot-travel-assistant"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Manual deployment of HOT Travel Assistant to Cloud Run"

# Set the project
gcloud config set project ${PROJECT_ID}

# Build the Docker image
echo "🐳 Building Docker image..."
docker build -t ${IMAGE_NAME} .

# Push to Container Registry
echo "📤 Pushing to Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},VERTEX_AI_LOCATION=us-central1,ENVIRONMENT=production,AI_PROVIDER=vertex,LLM_CACHE_DIR=/tmp/cache,LLM_CACHE_DURATION_HOURS=0" \
    --update-env-vars "AMADEUS_CLIENT_ID=DHdjRGkND0GefDhGAAbO7Gn5lr3EgG3P,AMADEUS_CLIENT_SECRET=x91XH0FoAqeBEV5h"

echo ""
echo "✅ Deployment completed!"
echo "🌐 Service URL:"
gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)"