# Google Official Vertex AI Cloud Run Deployment Guide

Following the official Google Cloud documentation:
**https://cloud.google.com/vertex-ai/generative-ai/docs/streamlit/create-cloudrun-service**

## 🎯 Official Google Approach vs Our Previous Method

### What Changed
- ✅ Using **Cloud Build** for container building (Google's recommendation)
- ✅ Using **Application Default Credentials** (proper authentication)
- ✅ Following **official service account pattern**
- ✅ Using **Google's recommended resource configuration**
- ✅ Implementing **proper health checks and probes**
- ✅ Using **official API enabling sequence**

### Key Differences from Generic Cloud Run
1. **Authentication**: Uses Application Default Credentials specifically for Vertex AI
2. **Service Account**: Uses the compute service account pattern
3. **Build Process**: Uses Cloud Build instead of local Docker push
4. **Configuration**: Follows Vertex AI application best practices
5. **Health Checks**: Implements comprehensive readiness/liveness probes

## 🚀 Quick Deployment (Google Official Method)

### Prerequisites
```bash
# 1. Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# 2. Authenticate (Corporate Account)
gcloud auth login
gcloud auth application-default login

# 3. Set your corporate project
gcloud config set project YOUR_CORPORATE_PROJECT_ID
```

### One-Command Deployment
```bash
# Deploy using Google's official method
./deploy-vertex-ai.sh
```

This script automatically:
- ✅ Validates prerequisites
- ✅ Enables required APIs in correct order
- ✅ Sets up Application Default Credentials
- ✅ Builds with Cloud Build (Google's way)
- ✅ Deploys with official Vertex AI configuration
- ✅ Tests the deployment

## 📋 Detailed Steps (Manual)

### Step 1: Project Setup
```bash
# Set your corporate project
gcloud config set project YOUR_CORPORATE_PROJECT_ID

# Verify access
gcloud projects describe YOUR_CORPORATE_PROJECT_ID
```

### Step 2: Enable APIs (Google's Required APIs)
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com  
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Step 3: Authentication (Google's Method)
```bash
# Set up Application Default Credentials (required for Vertex AI)
gcloud auth application-default login
```

### Step 4: Build with Cloud Build (Google's Recommendation)
```bash
# Build using Cloud Build (not local Docker)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hot-travel-assistant .
```

### Step 5: Deploy with Google's Configuration
```bash
# Get project number for service account
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

# Deploy with Google's recommended settings
gcloud run deploy hot-travel-assistant \
    --image gcr.io/YOUR_PROJECT_ID/hot-travel-assistant \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --concurrency 80 \
    --timeout 300 \
    --service-account "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,VERTEX_AI_LOCATION=us-central1,AI_PROVIDER=vertex,ENVIRONMENT=production"
```

## 🔒 Google's Authentication Pattern

### For Vertex AI Applications:
1. **Application Default Credentials** (not service account keys)
2. **Compute service account** for Cloud Run
3. **Proper IAM roles** automatically assigned

### Service Account Pattern:
```
${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
```

This is Google's recommended approach for Vertex AI applications.

## 📊 Google's Resource Recommendations

Based on the official documentation:

### For AI Applications:
- **Memory**: 2Gi (for AI model interactions)
- **CPU**: 2 vCPU (for processing requests)
- **Min Instances**: 1 (avoid cold starts)
- **Max Instances**: 10 (reasonable scaling)
- **Concurrency**: 80 requests per instance
- **Timeout**: 300s (for AI processing)

### Health Check Configuration:
- **Startup Probe**: 10s delay, check `/health`
- **Liveness Probe**: 30s delay, 10s interval
- **Readiness Probe**: 5s delay, 5s interval

## 🧪 Testing (Google's Method)

### Health Check
```bash
SERVICE_URL=$(gcloud run services describe hot-travel-assistant --region=us-central1 --format="value(status.url)")
curl $SERVICE_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "database": "connected",
  "api_version": "1.0.0"
}
```

### Test Vertex AI Integration
```bash
curl -X POST "$SERVICE_URL/travel/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Plan a trip to Tokyo for cherry blossom season",
    "nationality": "US",
    "email_id": "test@company.com"
  }'
```

## 📈 Monitoring (Google's Tools)

### View Logs
```bash
# Real-time logs
gcloud run services logs tail hot-travel-assistant --region=us-central1

# Historical logs
gcloud run services logs read hot-travel-assistant --region=us-central1
```

### Cloud Console
Visit: `https://console.cloud.google.com/run/detail/us-central1/hot-travel-assistant`

### Vertex AI Monitoring
Visit: `https://console.cloud.google.com/vertex-ai/models`

## 🔧 Advanced Configuration

### Using Secrets (Google's Way)
```bash
# Create secrets for API keys
echo -n "your-amadeus-id" | gcloud secrets create amadeus-client-id --data-file=-
echo -n "your-amadeus-secret" | gcloud secrets create amadeus-client-secret --data-file=-

# Deploy with secrets
gcloud run deploy hot-travel-assistant \
    --set-secrets "AMADEUS_CLIENT_ID=amadeus-client-id:latest,AMADEUS_CLIENT_SECRET=amadeus-client-secret:latest"
```

### Continuous Deployment (Google's Recommendation)
Set up Cloud Build triggers for automatic deployment on code changes.

## 🚨 Troubleshooting

### Common Issues:

**Authentication Errors**
```bash
# Fix: Ensure ADC is set
gcloud auth application-default login
```

**Vertex AI Access Denied**
```bash
# Fix: Check service account has Vertex AI roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

**Build Failures**
```bash
# Check Cloud Build logs
gcloud builds log $(gcloud builds list --limit=1 --format="value(id)")
```

## ✅ Benefits of Following Google's Official Method

1. **Optimal Performance**: Configured specifically for AI workloads
2. **Proper Authentication**: Uses Google's recommended patterns  
3. **Automatic Scaling**: Optimized for Vertex AI applications
4. **Integrated Monitoring**: Full Cloud Operations suite
5. **Security Best Practices**: Follows Google's security guidelines
6. **Official Support**: Backed by Google Cloud documentation

## 🎯 Ready to Deploy!

Use the official deployment script:
```bash
./deploy-vertex-ai.sh
```

This follows Google's exact recommendations for Vertex AI applications on Cloud Run!