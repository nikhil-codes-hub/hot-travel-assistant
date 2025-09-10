#!/bin/bash

# HOT Travel Assistant - Official Google Vertex AI Cloud Run Deployment
# Following: https://cloud.google.com/vertex-ai/generative-ai/docs/streamlit/create-cloudrun-service
set -e

echo "🤖 Google Vertex AI Cloud Run Deployment"
echo "Following official Google Cloud documentation"
echo "=========================================="

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="hot-travel-assistant"
IMAGE_NAME="gcr.io/\${PROJECT_ID}/${SERVICE_NAME}"

# Step 1: Validate prerequisites
echo "📋 Step 1: Validating prerequisites..."

# Check gcloud installation
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

echo "✅ Prerequisites validated"

# Step 2: Get project information
echo ""
echo "📋 Step 2: Project configuration..."

# Get current project
CURRENT_PROJECT=$(gcloud config get project 2>/dev/null || echo "")

if [ -z "$CURRENT_PROJECT" ]; then
    echo "❌ No project set. Please set your project:"
    echo "gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

PROJECT_ID=$CURRENT_PROJECT
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "✅ Using project: $PROJECT_ID"
echo "✅ Service name: $SERVICE_NAME"
echo "✅ Region: $REGION"
echo "✅ Image: $IMAGE_NAME"

# Step 3: Enable required APIs (following Google's documentation)
echo ""
echo "🔧 Step 3: Enabling required APIs..."
REQUIRED_APIS=(
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "containerregistry.googleapis.com"
    "aiplatform.googleapis.com"
    "secretmanager.googleapis.com"
)

for api in "\${REQUIRED_APIS[@]}"; do
    echo "   Enabling \$api..."
    gcloud services enable \$api --project=\$PROJECT_ID
done

echo "✅ APIs enabled"

# Step 4: Configure authentication (Application Default Credentials)
echo ""
echo "🔐 Step 4: Configuring authentication..."
echo "Ensuring Application Default Credentials are set..."

if ! gcloud auth application-default print-access-token &>/dev/null; then
    echo "⚠️  Setting up Application Default Credentials..."
    gcloud auth application-default login
fi

echo "✅ Authentication configured"

# Step 5: Build container image
echo ""
echo "🐳 Step 5: Building container image..."
echo "Building: \$IMAGE_NAME"

# Build with Cloud Build (Google's recommended approach)
gcloud builds submit --tag \$IMAGE_NAME .

echo "✅ Container image built and pushed"

# Step 6: Deploy to Cloud Run (following Google's best practices)
echo ""
echo "☁️ Step 6: Deploying to Cloud Run..."

# Get project number for service account
PROJECT_NUMBER=\$(gcloud projects describe \$PROJECT_ID --format="value(projectNumber)")

# Deploy with Google's recommended configuration
gcloud run deploy \$SERVICE_NAME \\
    --image \$IMAGE_NAME \\
    --platform managed \\
    --region \$REGION \\
    --allow-unauthenticated \\
    --port 8080 \\
    --memory 2Gi \\
    --cpu 2 \\
    --min-instances 1 \\
    --max-instances 10 \\
    --concurrency 80 \\
    --timeout 300 \\
    --service-account "\${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \\
    --set-env-vars "GOOGLE_CLOUD_PROJECT=\${PROJECT_ID}" \\
    --set-env-vars "VERTEX_AI_LOCATION=\${REGION}" \\
    --set-env-vars "AI_PROVIDER=vertex" \\
    --set-env-vars "ENVIRONMENT=production" \\
    --set-env-vars "LLM_CACHE_DIR=/tmp/cache" \\
    --set-env-vars "LLM_CACHE_DURATION_HOURS=0" \\
    --set-env-vars "AMADEUS_CLIENT_ID=DHdjRGkND0GefDhGAAbO7Gn5lr3EgG3P" \\
    --set-env-vars "AMADEUS_CLIENT_SECRET=x91XH0FoAqeBEV5h"

# Get service URL
SERVICE_URL=\$(gcloud run services describe \$SERVICE_NAME --region=\$REGION --format="value(status.url)")

echo ""
echo "🎉 Deployment completed successfully!"
echo "=========================================="
echo "📊 Service Details:"
echo "   Project: \$PROJECT_ID"
echo "   Service: \$SERVICE_NAME"
echo "   Region: \$REGION"
echo "   URL: \$SERVICE_URL"
echo ""
echo "🔍 Endpoints:"
echo "   Health Check: \${SERVICE_URL}/health"
echo "   API: \${SERVICE_URL}/travel/search"
echo ""
echo "📝 Management:"
echo "   Logs: gcloud run services logs tail \$SERVICE_NAME --region=\$REGION"
echo "   Console: https://console.cloud.google.com/run/detail/\$REGION/\$SERVICE_NAME?project=\$PROJECT_ID"
echo ""

# Step 7: Test deployment
echo "🧪 Step 7: Testing deployment..."
sleep 5  # Wait for service to be fully ready

echo "   Testing health endpoint..."
if curl -f -s "\${SERVICE_URL}/health" >/dev/null; then
    echo "✅ Health check passed!"
    echo ""
    echo "🎯 Your Vertex AI-powered Travel Assistant is live!"
    echo "   Ready to handle travel requests with full AI capabilities"
else
    echo "⚠️  Health check failed. Checking logs..."
    gcloud run services logs read \$SERVICE_NAME --region=\$REGION --limit=10
fi

echo ""
echo "📚 Next steps:"
echo "1. Test with: curl \${SERVICE_URL}/health"
echo "2. Monitor: gcloud run services logs tail \$SERVICE_NAME --region=\$REGION"
echo "3. Scale: gcloud run services update \$SERVICE_NAME --max-instances=20"