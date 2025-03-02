# Pedestrian Detection and Depth Estimation Dataflow Pipeline

This project sets up a Google Cloud Dataflow pipeline that processes images from a Pub/Sub topic, performs pedestrian detection and depth estimation using PyTorch models, and outputs the results to another Pub/Sub topic.

## Prerequisites

- Google Cloud Platform account with:
  - Dataflow API enabled
  - Pub/Sub API enabled
  - Storage API enabled
  - A service account with permissions for Dataflow, Pub/Sub, and Storage
- Docker installed locally
- Google Cloud SDK (gcloud) installed

## Setup

1. Clone this repository to your local machine.

2. Create a GCS bucket for the Dataflow job:

   ```
   gsutil mb gs://your-bucket-name/
   ```

3. Create the required Pub/Sub topics and subscriptions:

   ```
   # Create the input topic (if not already existing)
   gcloud pubsub topics create design3-sub --project=your-project-id

   # Create the output topic
   gcloud pubsub topics create pedestrian-detection-output --project=your-project-id
   
   # Create a subscription for the output topic
   gcloud pubsub subscriptions create pedestrian-detection-output-sub --topic=pedestrian-detection-output --project=your-project-id
   ```

4. Place your service account key JSON file in the project directory.

## Running the Pipeline

1. Make the run script executable:

   ```
   chmod +x run_pipeline.sh
   ```

2. Run the pipeline:

   ```
   ./run_pipeline.sh --project=your-project-id --bucket=your-bucket-name
   ```

3. To publish test images to the input topic:

   ```
   python publisher.py --project=your-project-id --topic=design3-sub --folder=./Dataset_Occluded_Pedestrian
   ```

4. To visualize the results:

   ```
   python subscriber1.py --project=your-project-id --subscription=pedestrian-detection-output-sub
   ```

## Pipeline Components

- `pedestrian_detection_dataflow.py`: The main Dataflow pipeline
- `publisher.py`: Utility to publish images to the input topic
- `subscriber1.py`: Utility to subscribe to results and visualize bounding boxes

## Docker

The pipeline uses a Docker container for consistent execution environment across Dataflow workers. The Dockerfile is included in this repository.

## Models

The pipeline uses:

- Faster R-CNN with ResNet-50 FPN for pedestrian detection
- MiDaS small model for depth estimation

Both models are loaded from torchvision and torch hub respectively at runtime.
