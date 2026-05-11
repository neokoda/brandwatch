#!/usr/bin/env bash
# Deploy backend to Cloud Run (asia-southeast1)
# Run from the project root: bash deploy/deploy.sh

set -e

PROJECT_ID="tsunami-sentiment"
REGION="asia-southeast1"
SERVICE="brandwatch-backend"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}"

echo "==> Building and pushing image to GCR..."
gcloud builds submit \
  --tag "${IMAGE}" \
  --project "${PROJECT_ID}" \
  .

echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --port 8080 \
  --env-vars-file deploy/cloudrun-env.yaml \
  --project "${PROJECT_ID}"

echo ""
echo "==> Done. Backend URL:"
gcloud run services describe "${SERVICE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)"
