#!/bin/bash

# TBMM API Deployment Script for Google Cloud Run
# Usage: ./deploy.sh [elasticsearch-ip]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   TBMM API Deployment to Cloud Run    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: No GCP project set${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✓ GCP Project: ${PROJECT_ID}${NC}"

# Get Elasticsearch host
if [ -z "$1" ]; then
    echo -e "${YELLOW}Enter your Elasticsearch host (e.g., http://34.159.123.45:9200):${NC}"
    read -r ES_HOST
else
    ES_HOST="http://$1:9200"
fi

if [ -z "$ES_HOST" ]; then
    echo -e "${RED}❌ Error: Elasticsearch host is required${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Elasticsearch: ${ES_HOST}${NC}"

# Configuration
SERVICE_NAME="tbmm-api"
REGION="europe-west3"
ES_INDEX="parliament_speeches"

echo ""
echo -e "${BLUE}📋 Deployment Configuration:${NC}"
echo "   Service: ${SERVICE_NAME}"
echo "   Region: ${REGION}"
echo "   ES Host: ${ES_HOST}"
echo "   ES Index: ${ES_INDEX}"
echo ""

# Confirm deployment
echo -e "${YELLOW}Deploy to Cloud Run? (y/n)${NC}"
read -r CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
echo ""

# Deploy
gcloud run deploy ${SERVICE_NAME} \
  --source . \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars ELASTICSEARCH_HOST=${ES_HOST} \
  --set-env-vars ELASTICSEARCH_INDEX=${ES_INDEX} \
  --set-env-vars CORS_ORIGINS="*" \
  --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      ✅ Deployment Successful!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🌐 Your API is live at:${NC}"
echo -e "${GREEN}   ${SERVICE_URL}${NC}"
echo ""
echo -e "${BLUE}📝 Test your API:${NC}"
echo "   Health check:  curl ${SERVICE_URL}/health"
echo "   List MPs:      curl ${SERVICE_URL}/api/mps"
echo "   Documentation: ${SERVICE_URL}/docs"
echo ""
echo -e "${BLUE}📊 View logs:${NC}"
echo "   gcloud run logs read --service=${SERVICE_NAME} --region=${REGION}"
echo ""
echo -e "${BLUE}🔧 Manage service:${NC}"
echo "   Console: https://console.cloud.google.com/run?project=${PROJECT_ID}"
echo ""

# Test health endpoint
echo -e "${BLUE}🔍 Testing health endpoint...${NC}"
sleep 5  # Wait for service to be fully ready

if curl -s "${SERVICE_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API is healthy and connected to Elasticsearch!${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Health check returned unexpected response${NC}"
    echo "   Check logs: gcloud run logs read --service=${SERVICE_NAME}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
