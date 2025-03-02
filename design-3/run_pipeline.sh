#!/bin/bash

# Exit on error
set -e

# Default values
PROJECT_ID=""
INPUT_TOPIC="design3-sub"  # As specified in your requirements
OUTPUT_TOPIC="pedestrian-detection-output"
REGION="us-central1"
JOB_NAME="pedestrian-detection-dataflow"
BUCKET_NAME=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --project)
      PROJECT_ID="$2"
      shift
      shift
      ;;
    --bucket)
      BUCKET_NAME="$2"
      shift
      shift
      ;;
    --region)
      REGION="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required parameters
if [ -z "$PROJECT_ID" ]; then
  echo "Error: --project is required"
  exit 1
fi

if [ -z "$BUCKET_NAME" ]; then
  echo "Error: --bucket is required"
  exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/pedestrian-detection:latest .

# Push the image to Google Container Registry
echo "Pushing Docker image to GCR..."
docker push gcr.io/$PROJECT_ID/pedestrian-detection:latest

# Run the Dataflow job
echo "Launching Dataflow job..."
python pedestrian_detection_dataflow.py \
  --input_topic=projects/$PROJECT_ID/topics/$INPUT_TOPIC \
  --output_topic=projects/$PROJECT_ID/topics/$OUTPUT_TOPIC \
  --project=$PROJECT_ID \
  --region=$REGION \
  --job_name=$JOB_NAME \
  --temp_location=gs://$BUCKET_NAME/temp \
  --staging_location=gs://$BUCKET_NAME/staging \
  --requirements_file=requirements.txt \
  --runner=DataflowRunner \
  --setup_file=./setup.py \
  --worker_container_image=gcr.io/$PROJECT_ID/pedestrian-detection:latest

echo "Pipeline launched successfully!"
echo "To view the results, run the subscriber script:"
echo "python subscriber1.py --project=$PROJECT_ID --subscription=$OUTPUT_TOPIC-sub"
