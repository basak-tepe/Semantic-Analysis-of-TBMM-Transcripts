# Deployment Guide

This guide covers deploying the TBMM API to Google Cloud Run.

## Prerequisites

1. GCP account with billing enabled
2. `gcloud` CLI installed and authenticated
3. Elasticsearch instance running (see below)
4. Docker installed (for local testing)

## Quick Deploy to GCP Cloud Run

### 1. Set Environment Variables

```bash
# Your GCP project ID
export PROJECT_ID="your-project-id"

# Your Elasticsearch host (e.g., GCP VM IP or Elastic Cloud URL)
export ES_HOST="http://YOUR_VM_IP:9200"

# Your Elasticsearch index name
export ES_INDEX="parliament_speeches"

# Set project
gcloud config set project $PROJECT_ID
```

### 2. Deploy to Cloud Run

```bash
# Deploy from source (Cloud Run will build using Dockerfile)
gcloud run deploy tbmm-api \
  --source . \
  --region europe-west3 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars ELASTICSEARCH_HOST=$ES_HOST \
  --set-env-vars ELASTICSEARCH_INDEX=$ES_INDEX \
  --set-env-vars CORS_ORIGINS="*"
```

### 3. Get Your API URL

After deployment completes, Cloud Run will show:
```
Service URL: https://tbmm-api-xxxxx-ew.a.run.app
```

### 4. Test Your Deployment

```bash
# Health check
curl https://YOUR_CLOUD_RUN_URL/health

# List MPs
curl https://YOUR_CLOUD_RUN_URL/api/mps
```

## Elasticsearch Setup

### Option 1: GCP VM (Recommended for Turkey)

```bash
# Create VM in Frankfurt (closest to Turkey)
gcloud compute instances create tbmm-elasticsearch \
  --zone=europe-west3-a \
  --machine-type=e2-medium \
  --boot-disk-size=50GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=elasticsearch

# Open firewall
gcloud compute firewall-rules create allow-elasticsearch \
  --allow tcp:9200 \
  --target-tags=elasticsearch

# SSH and install (see main README for full installation steps)
gcloud compute ssh tbmm-elasticsearch --zone=europe-west3-a
```

### Option 2: Elastic Cloud

Sign up at https://cloud.elastic.co/ and use the provided URL.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ELASTICSEARCH_HOST` | ES connection URL | `http://34.159.123.45:9200` |
| `ELASTICSEARCH_INDEX` | Index name | `parliament_speeches` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `*` or `https://yourdomain.com` |

## Local Testing with Docker

```bash
# Build image
docker build -t tbmm-api .

# Run locally
docker run -p 8080:8080 \
  -e ELASTICSEARCH_HOST=http://localhost:9200 \
  -e ELASTICSEARCH_INDEX=parliament_speeches \
  -e CORS_ORIGINS="*" \
  tbmm-api

# Test
curl http://localhost:8080/health
```

## Updating the Deployment

```bash
# Simply re-run the deploy command
gcloud run deploy tbmm-api \
  --source . \
  --region europe-west3
```

Cloud Run will rebuild and deploy automatically.

## Monitoring & Logs

```bash
# View logs
gcloud run logs read --service=tbmm-api --region=europe-west3

# Follow logs in real-time
gcloud run logs tail --service=tbmm-api --region=europe-west3
```

## Cost Optimization

```bash
# Set minimum instances to 0 (scale to zero when idle)
gcloud run services update tbmm-api \
  --region europe-west3 \
  --min-instances 0

# Set maximum instances
gcloud run services update tbmm-api \
  --region europe-west3 \
  --max-instances 5
```

## Security Best Practices

1. **Enable CORS properly**: Replace `CORS_ORIGINS="*"` with specific domains in production
2. **Use Secret Manager** for sensitive data:
   ```bash
   echo -n "your-es-password" | gcloud secrets create es-password --data-file=-
   gcloud run services update tbmm-api \
     --set-secrets=ELASTICSEARCH_PASSWORD=es-password:latest
   ```
3. **Restrict Elasticsearch access**: Use VPC connector or firewall rules to limit ES access

## Troubleshooting

### Deployment fails
```bash
# Check build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

### Service not accessible
```bash
# Check service status
gcloud run services describe tbmm-api --region=europe-west3

# Check if unauthenticated access is allowed
gcloud run services get-iam-policy tbmm-api --region=europe-west3
```

### Cannot connect to Elasticsearch
```bash
# Test from Cloud Run
gcloud run services proxy tbmm-api --region=europe-west3

# Then in another terminal:
curl http://localhost:8080/health
```

## Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=tbmm-api \
  --region=europe-west3 \
  --domain=api.yourdomain.com
```

## Support

For issues, check:
- Cloud Run logs: `gcloud run logs read`
- Elasticsearch logs: SSH to VM and check `/var/log/elasticsearch/`
- API health: `curl https://YOUR_URL/health`
