#!/bin/bash

# Cloud Run Deployment Script for HOT Travel Assistant
# Run this script from the project root directory

echo "🚀 Starting Cloud Run deployment process..."

# Step 1: Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Step 2: List available projects and set project
echo "📋 Available GCP projects:"
gcloud projects list

echo ""
read -p "Enter your GCP Project ID: " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID cannot be empty"
    exit 1
fi

# Step 3: Set the project
echo "🔧 Setting GCP project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Step 4: Verify project is set
CURRENT_PROJECT=$(gcloud config get-value project)
echo "✅ Current project: $CURRENT_PROJECT"

# Step 5: Enable required APIs
echo "🔌 Enabling Cloud Run API..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Step 6: Set default region (optional)
echo "🌍 Setting default region to us-central1..."
gcloud config set run/region us-central1

echo ""
echo "===================================================="
echo "🎯 Ready to deploy! Run these commands:"
echo "===================================================="
echo ""

echo "1️⃣ Deploy Backend (from project root):"
echo "gcloud run deploy hot-travel-backend \\"
echo "  --source . \\"
echo "  --allow-unauthenticated \\"
echo "  --region us-central1"
echo ""

echo "2️⃣ Deploy Frontend (from frontend directory):"
echo "cd frontend"
echo "gcloud run deploy hot-travel-frontend \\"
echo "  --source . \\"
echo "  --allow-unauthenticated \\"
echo "  --region us-central1"
echo ""

echo "===================================================="
echo "📝 Post-deployment steps:"
echo "===================================================="
echo "1. Note the backend URL from the first deployment"
echo "2. Update frontend API calls to use the backend URL"
echo "3. Test both services"
echo ""

echo "🎉 Setup complete! You can now run the deployment commands above."