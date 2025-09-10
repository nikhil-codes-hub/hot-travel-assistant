# HOT Travel Assistant - Cloud Run Deployment Guide

This guide walks you through deploying the HOT Intelligent Travel Assistant to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed (for manual deployment)
4. **Project ID**: `ace-agility-304513`

## Quick Deployment

### Option 1: Automated Deployment (Recommended)

```bash
# Make sure you're in the project directory
cd /path/to/hot_intelligent_travel_assistant

# Run the automated deployment script
./deploy.sh
```

### Option 2: Manual Deployment

```bash
# Run the manual deployment script
./deploy-manual.sh
```

### Option 3: Cloud Build Deployment

```bash
# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml .
```

## Step-by-Step Manual Process

### 1. Authentication & Project Setup

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set the project
gcloud config set project ace-agility-304513

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 2. Build and Push Docker Image

```bash
# Build the Docker image
docker build -t gcr.io/ace-agility-304513/hot-travel-assistant .

# Push to Container Registry
docker push gcr.io/ace-agility-304513/hot-travel-assistant
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy hot-travel-assistant \
    --image gcr.io/ace-agility-304513/hot-travel-assistant \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=ace-agility-304513,VERTEX_AI_LOCATION=us-central1,ENVIRONMENT=production,AI_PROVIDER=vertex,LLM_CACHE_DIR=/tmp/cache,LLM_CACHE_DURATION_HOURS=0,AMADEUS_CLIENT_ID=DHdjRGkND0GefDhGAAbO7Gn5lr3EgG3P,AMADEUS_CLIENT_SECRET=x91XH0FoAqeBEV5h"
```

## Environment Configuration

The application uses these environment variables:

- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID
- `VERTEX_AI_LOCATION`: Region for Vertex AI (us-central1)
- `ENVIRONMENT`: Set to "production"
- `AI_PROVIDER`: Set to "vertex" for Vertex AI
- `LLM_CACHE_DIR`: Cache directory for LLM responses
- `LLM_CACHE_DURATION_HOURS`: Cache duration (0 = no caching)
- `AMADEUS_CLIENT_ID`: Amadeus API client ID
- `AMADEUS_CLIENT_SECRET`: Amadeus API client secret

## Service Configuration

- **Memory**: 2GB
- **CPU**: 2 vCPU
- **Port**: 8080
- **Min Instances**: 1
- **Max Instances**: 10
- **Region**: us-central1

## Post-Deployment

### 1. Test the Service

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe hot-travel-assistant --region=us-central1 --format="value(status.url)")

# Test health endpoint
curl ${SERVICE_URL}/health

# Test the API
curl -X POST "${SERVICE_URL}/travel/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "I want to visit Tokyo for cherry blossom season",
    "nationality": "US",
    "email_id": "test@example.com"
  }'
```

### 2. View Logs

```bash
# View real-time logs
gcloud logs tail --follow --project=ace-agility-304513

# View service-specific logs
gcloud run services logs read hot-travel-assistant --region=us-central1
```

### 3. Monitor Performance

```bash
# Check service status
gcloud run services describe hot-travel-assistant --region=us-central1

# View metrics in Cloud Console
# https://console.cloud.google.com/run/detail/us-central1/hot-travel-assistant
```

## Security Best Practices

### 1. Use Secret Manager (When Billing is Enabled)

```bash
# Create secrets for API keys
echo -n "your-amadeus-client-id" | gcloud secrets create amadeus-client-id --data-file=-
echo -n "your-amadeus-client-secret" | gcloud secrets create amadeus-client-secret --data-file=-

# Update deployment to use secrets
gcloud run deploy hot-travel-assistant \
    --set-secrets "AMADEUS_CLIENT_ID=amadeus-client-id:latest,AMADEUS_CLIENT_SECRET=amadeus-client-secret:latest"
```

### 2. Enable IAM Authentication

```bash
# Remove public access
gcloud run services remove-iam-policy-binding hot-travel-assistant \
    --region=us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"

# Grant access to specific users/service accounts
gcloud run services add-iam-policy-binding hot-travel-assistant \
    --region=us-central1 \
    --member="user:your-email@domain.com" \
    --role="roles/run.invoker"
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   gcloud auth application-default login
   ```

2. **Build Failures**
   ```bash
   # Check Docker is running
   docker version
   
   # Check permissions
   gcloud auth configure-docker
   ```

3. **Service Not Starting**
   ```bash
   # Check logs
   gcloud run services logs read hot-travel-assistant --region=us-central1 --limit=50
   ```

4. **Environment Variable Issues**
   ```bash
   # Update environment variables
   gcloud run services update hot-travel-assistant \
       --region=us-central1 \
       --update-env-vars "KEY=VALUE"
   ```

## Scaling Configuration

### Auto-scaling Settings

```bash
# Update scaling configuration
gcloud run services update hot-travel-assistant \
    --region=us-central1 \
    --min-instances=1 \
    --max-instances=20 \
    --concurrency=80 \
    --cpu=2 \
    --memory=4Gi
```

### Cost Optimization

- Set `--min-instances=0` for development
- Use `--cpu=1` and `--memory=1Gi` for light workloads
- Monitor usage in Cloud Console

## Continuous Deployment

Set up automated deployment using Cloud Build triggers:

1. Connect your GitHub repository
2. Create a build trigger
3. Use the provided `cloudbuild.yaml` configuration

## Support

- **Logs**: Use `gcloud logs` commands above
- **Monitoring**: Cloud Console > Cloud Run
- **Documentation**: https://cloud.google.com/run/docs

The service should now be running at your Cloud Run URL and ready to handle travel requests!