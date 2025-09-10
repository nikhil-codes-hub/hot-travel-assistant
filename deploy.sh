#!/bin/bash

# HOT Travel Assistant Cloud Run Deployment Script
set -e

# Configuration
PROJECT_ID="ace-agility-304513"
SERVICE_NAME="hot-travel-assistant"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Starting deployment of HOT Travel Assistant to Cloud Run"
echo "📋 Project ID: ${PROJECT_ID}"
echo "🌍 Region: ${REGION}"
echo "🐳 Image: ${IMAGE_NAME}"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check authentication
echo "🔐 Checking authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not authenticated with gcloud. Please run:"
    echo "gcloud auth login"
    exit 1
fi

# Set the project
echo "📋 Setting project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Note: Using environment variables instead of secrets for now
# Secrets require billing to be enabled on the project

# Build and deploy using Cloud Build
echo "🔨 Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Service URL:"
gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)"
echo ""
echo "📊 Service status:"
gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="table(status.conditions[0].type:label=STATUS, status.conditions[0].status)"
echo ""
echo "🔍 To view logs:"
echo "gcloud logs tail --follow --source-type=\"gce_instance\""
echo ""
echo "🚀 Your HOT Travel Assistant is now live on Cloud Run!"