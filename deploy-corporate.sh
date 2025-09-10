#!/bin/bash

# HOT Travel Assistant Corporate GCP Deployment Script
set -e

echo "🏢 Corporate GCP Deployment for HOT Travel Assistant"
echo "=================================================="

# Load configuration
if [ ! -f "corporate-config.env" ]; then
    echo "❌ Error: corporate-config.env file not found!"
    echo "📋 Please copy corporate-config.env and update with your corporate GCP details"
    echo "   1. Update CORPORATE_PROJECT_ID"
    echo "   2. Update CORPORATE_REGION if needed"
    echo "   3. Update API keys if using corporate Amadeus account"
    exit 1
fi

source corporate-config.env

# Validate required variables
if [ "$CORPORATE_PROJECT_ID" == "your-corporate-project-id" ]; then
    echo "❌ Error: Please update CORPORATE_PROJECT_ID in corporate-config.env"
    exit 1
fi

echo "📋 Configuration:"
echo "   Project ID: $CORPORATE_PROJECT_ID"
echo "   Region: $CORPORATE_REGION"
echo "   Service Name: $CORPORATE_SERVICE_NAME"
echo ""

# Check authentication
echo "🔐 Checking gcloud authentication..."
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
if [ -z "$CURRENT_ACCOUNT" ]; then
    echo "❌ Not authenticated with gcloud."
    echo "📝 Please authenticate with your corporate account:"
    echo "   gcloud auth login"
    echo "   gcloud auth application-default login"
    exit 1
fi

echo "✅ Authenticated as: $CURRENT_ACCOUNT"

# Set the project
echo "📋 Setting project to $CORPORATE_PROJECT_ID..."
gcloud config set project $CORPORATE_PROJECT_ID

# Check if project exists and is accessible
echo "🔍 Verifying project access..."
if ! gcloud projects describe $CORPORATE_PROJECT_ID >/dev/null 2>&1; then
    echo "❌ Cannot access project $CORPORATE_PROJECT_ID"
    echo "💡 Please verify:"
    echo "   1. Project ID is correct"
    echo "   2. Your account has access to the project"
    echo "   3. Billing is enabled on the project"
    exit 1
fi

echo "✅ Project access verified"

# Enable required APIs
echo "🔧 Enabling required APIs..."
echo "   This may take a few minutes..."
REQUIRED_APIS=(
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "containerregistry.googleapis.com"
    "aiplatform.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    echo "   Enabling $api..."
    if ! gcloud services enable $api; then
        echo "❌ Failed to enable $api"
        echo "💡 Please check if your account has the necessary permissions"
        echo "   Required roles: Cloud Build Editor, Cloud Run Admin, Storage Admin"
        exit 1
    fi
done

echo "✅ All required APIs enabled"

# Build the image name
IMAGE_NAME="gcr.io/${CORPORATE_PROJECT_ID}/${CORPORATE_SERVICE_NAME}"
echo "🐳 Docker image: $IMAGE_NAME"

# Build and push the Docker image
echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "📤 Pushing to Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $CORPORATE_SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $CORPORATE_REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory $MEMORY \
    --cpu $CPU \
    --max-instances $MAX_INSTANCES \
    --min-instances $MIN_INSTANCES \
    --concurrency $CONCURRENCY \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${CORPORATE_PROJECT_ID},VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION},ENVIRONMENT=${ENVIRONMENT},AI_PROVIDER=${AI_PROVIDER},LLM_CACHE_DIR=${LLM_CACHE_DIR},LLM_CACHE_DURATION_HOURS=${LLM_CACHE_DURATION_HOURS},AMADEUS_CLIENT_ID=${AMADEUS_CLIENT_ID},AMADEUS_CLIENT_SECRET=${AMADEUS_CLIENT_SECRET}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $CORPORATE_SERVICE_NAME --region=$CORPORATE_REGION --format="value(status.url)")

echo ""
echo "🎉 Deployment completed successfully!"
echo "=================================================="
echo "🌐 Service URL: $SERVICE_URL"
echo "🔍 Health Check: ${SERVICE_URL}/health"
echo "📊 API Endpoint: ${SERVICE_URL}/travel/search"
echo ""
echo "📝 Next steps:"
echo "   1. Test the health endpoint: curl ${SERVICE_URL}/health"
echo "   2. View logs: gcloud run services logs read $CORPORATE_SERVICE_NAME --region=$CORPORATE_REGION"
echo "   3. Monitor: https://console.cloud.google.com/run/detail/${CORPORATE_REGION}/${CORPORATE_SERVICE_NAME}"
echo ""
echo "🎯 Your HOT Travel Assistant is now live on your corporate GCP account!"

# Test the deployment
echo "🧪 Testing deployment..."
echo "   Testing health endpoint..."
if curl -f -s "${SERVICE_URL}/health" >/dev/null; then
    echo "✅ Health check passed!"
else
    echo "⚠️  Health check failed - check logs for details"
fi