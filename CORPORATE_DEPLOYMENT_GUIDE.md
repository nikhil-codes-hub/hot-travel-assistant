# Corporate GCP Deployment Guide
## HOT Travel Assistant - Detailed Step-by-Step Instructions

This guide provides detailed instructions for deploying the HOT Travel Assistant to your corporate Google Cloud Platform account.

## 🎯 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Access to a corporate GCP account with billing enabled
- [ ] Required permissions (Cloud Build Editor, Cloud Run Admin, Storage Admin)
- [ ] gcloud CLI installed on your machine
- [ ] Docker installed and running
- [ ] Corporate project ID from your GCP admin

## 📋 Step 1: Get Corporate GCP Information

Contact your GCP administrator or check Google Cloud Console to get:

1. **Project ID** (e.g., `company-travel-prod-2024`)
2. **Preferred region** (e.g., `us-central1`, `europe-west1`)
3. **Any corporate naming conventions** for services
4. **Required permissions/roles** (if not already assigned)

## 🔧 Step 2: Configure Your Local Environment

### A. Authenticate with Corporate Account

```bash
# Logout from personal account (if logged in)
gcloud auth revoke --all

# Login with your corporate account
gcloud auth login
# Follow the browser authentication flow

# Set application default credentials
gcloud auth application-default login
# Follow the browser authentication flow again
```

### B. Verify Authentication

```bash
# Check current authenticated account
gcloud auth list

# Should show your corporate email as ACTIVE
# Example output:
#        Credentialed Accounts
# ACTIVE: john.doe@company.com
#         personal.email@gmail.com
```

## 📝 Step 3: Configure Corporate Settings

### A. Edit Configuration File

```bash
# Copy the template configuration
cp corporate-config.env my-corporate-config.env

# Edit the configuration
nano my-corporate-config.env  # or use your preferred editor
```

### B. Update Required Values

Replace these values in `my-corporate-config.env`:

```bash
# CRITICAL: Update this with your corporate project ID
CORPORATE_PROJECT_ID="your-company-project-id"

# Update region if different (check with your admin)
CORPORATE_REGION="us-central1"

# Optional: Update service name per corporate naming conventions
CORPORATE_SERVICE_NAME="hot-travel-assistant"

# If your company has corporate Amadeus API keys, update these:
AMADEUS_CLIENT_ID="your-corporate-amadeus-id"
AMADEUS_CLIENT_SECRET="your-corporate-amadeus-secret"
```

### C. Rename Configuration File

```bash
# Rename to match what the script expects
mv my-corporate-config.env corporate-config.env
```

## 🚀 Step 4: Deploy to Corporate GCP

### Option 1: Automated Deployment (Recommended)

```bash
# Run the corporate deployment script
./deploy-corporate.sh
```

The script will:
1. ✅ Validate your configuration
2. ✅ Check authentication
3. ✅ Set the correct project
4. ✅ Enable required APIs
5. ✅ Build Docker image
6. ✅ Push to Container Registry
7. ✅ Deploy to Cloud Run
8. ✅ Test the deployment

### Option 2: Manual Step-by-Step Deployment

If you prefer manual control:

```bash
# 1. Set project
gcloud config set project YOUR_CORPORATE_PROJECT_ID

# 2. Enable APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com

# 3. Build image
docker build -t gcr.io/YOUR_CORPORATE_PROJECT_ID/hot-travel-assistant .

# 4. Push image
docker push gcr.io/YOUR_CORPORATE_PROJECT_ID/hot-travel-assistant

# 5. Deploy to Cloud Run
gcloud run deploy hot-travel-assistant \
    --image gcr.io/YOUR_CORPORATE_PROJECT_ID/hot-travel-assistant \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=YOUR_CORPORATE_PROJECT_ID,VERTEX_AI_LOCATION=us-central1,ENVIRONMENT=production,AI_PROVIDER=vertex,LLM_CACHE_DIR=/tmp/cache,LLM_CACHE_DURATION_HOURS=0,AMADEUS_CLIENT_ID=YOUR_AMADEUS_ID,AMADEUS_CLIENT_SECRET=YOUR_AMADEUS_SECRET"
```

## 🧪 Step 5: Test the Deployment

### A. Basic Health Check

```bash
# Get service URL (script will show this)
SERVICE_URL="https://hot-travel-assistant-[hash]-uc.a.run.app"

# Test health endpoint
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

### B. Test Travel Search API

```bash
curl -X POST "$SERVICE_URL/travel/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "I want to visit Tokyo for cherry blossom season in March",
    "nationality": "US",
    "email_id": "test@company.com"
  }'
```

### C. Test Vertex AI Integration

```bash
curl -X GET "$SERVICE_URL/travel/visa-requirements?origin_country=US&destination_country=JP"
```

## 📊 Step 6: Monitor and Manage

### A. View Logs

```bash
# Real-time logs
gcloud run services logs tail hot-travel-assistant --region=us-central1

# Recent logs
gcloud run services logs read hot-travel-assistant --region=us-central1 --limit=50
```

### B. Update Service

```bash
# Update environment variables
gcloud run services update hot-travel-assistant \
    --region us-central1 \
    --update-env-vars "NEW_VAR=new_value"

# Update scaling
gcloud run services update hot-travel-assistant \
    --region us-central1 \
    --max-instances 20 \
    --min-instances 2
```

### C. Cloud Console Access

Visit: `https://console.cloud.google.com/run/detail/us-central1/hot-travel-assistant?project=YOUR_PROJECT_ID`

## 🔒 Step 7: Security Configuration (Corporate Best Practices)

### A. Restrict Public Access (Optional)

```bash
# Remove public access
gcloud run services remove-iam-policy-binding hot-travel-assistant \
    --region us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"

# Add specific corporate users
gcloud run services add-iam-policy-binding hot-travel-assistant \
    --region us-central1 \
    --member="user:team@company.com" \
    --role="roles/run.invoker"
```

### B. Use Corporate Service Account

```bash
# Deploy with custom service account
gcloud run deploy hot-travel-assistant \
    --service-account your-service-account@your-project.iam.gserviceaccount.com \
    --region us-central1
```

## 🚨 Troubleshooting Guide

### Issue: Authentication Failed
```bash
# Solution: Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### Issue: Permission Denied
```bash
# Check required roles:
gcloud projects get-iam-policy YOUR_PROJECT_ID \
    --filter="bindings.members:user:your-email@company.com"

# Required roles:
# - roles/run.admin
# - roles/cloudbuild.builds.editor
# - roles/storage.admin
```

### Issue: API Not Enabled
```bash
# Enable manually
gcloud services enable run.googleapis.com --project=YOUR_PROJECT_ID
```

### Issue: Build Fails
```bash
# Check Docker is running
docker version

# Check authentication to registry
gcloud auth configure-docker
```

### Issue: Service Won't Start
```bash
# Check logs for errors
gcloud run services logs read hot-travel-assistant --region=us-central1 --limit=100

# Common issues:
# - Port configuration (should be 8080)
# - Environment variables
# - Memory/CPU limits
```

## 📈 Cost Monitoring

Expected costs for corporate usage:

- **Light usage** (< 1000 requests/day): $5-15/month
- **Medium usage** (< 10,000 requests/day): $20-50/month  
- **Heavy usage** (> 50,000 requests/day): $100-300/month

Monitor costs at: `https://console.cloud.google.com/billing`

## 🎯 Production Recommendations

1. **Enable monitoring**: Set up Cloud Monitoring alerts
2. **Use secrets**: Migrate API keys to Secret Manager
3. **Set up CI/CD**: Automate deployments from your code repository
4. **Load testing**: Test with expected corporate traffic
5. **Backup strategy**: Regular exports of any stored data

## 📞 Support

If you encounter issues:

1. **Check logs**: `gcloud run services logs read hot-travel-assistant`
2. **Verify permissions**: Contact your GCP administrator
3. **Corporate policies**: Some companies have restrictions on certain APIs
4. **Network policies**: Corporate firewalls may affect external API calls

Your HOT Travel Assistant should now be running successfully on your corporate GCP account! 🎉