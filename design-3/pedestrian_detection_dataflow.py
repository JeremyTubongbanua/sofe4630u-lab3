#!/usr/bin/env python3
import argparse
import io
import json
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, SetupOptions, GoogleCloudOptions, WorkerOptions
import torch
import torchvision
import numpy as np
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F
import glob
import os

files = glob.glob("*.json")
if files:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = files[0]

logging.getLogger().setLevel(logging.INFO)

class ProcessImageDoFn(beam.DoFn):
    def setup(self):
        logging.info("Setting up models...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info(f"Using device: {self.device}")
        
        # Load detection model
        logging.info("Loading detection model...")
        self.detection_model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
        self.detection_model.to(self.device)
        self.detection_model.eval()
        
        # Load depth estimation model
        logging.info("Loading depth estimation model...")
        self.midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
        self.midas.to(self.device)
        self.midas.eval()
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        self.midas_transform = midas_transforms.small_transform
        logging.info("Models loaded successfully")

    def detect_pedestrians(self, image):
        transform = T.ToTensor()
        image_tensor = transform(image).to(self.device)
        with torch.no_grad():
            detections = self.detection_model([image_tensor])[0]
        pedestrian_bboxes = []
        for box, label, score in zip(detections["boxes"], detections["labels"], detections["scores"]):
            if label.item() == 1 and score.item() >= 0.5:  # 1 is the label for 'person' in COCO
                pedestrian_bboxes.append(box.cpu().numpy().tolist())
        return pedestrian_bboxes

    def estimate_depth(self, image):
        image_np = np.array(image)
        transformed = self.midas_transform(image_np)
        if isinstance(transformed, dict) and "image" in transformed:
            input_depth = transformed["image"]
        else:
            input_depth = transformed
        if not torch.is_tensor(input_depth):
            input_depth = torch.from_numpy(input_depth)
        input_depth = input_depth.to(self.device)
        if input_depth.ndim == 3:
            input_depth = input_depth.unsqueeze(0)
        with torch.no_grad():
            depth_prediction = self.midas(input_depth)
        orig_width, orig_height = image.size
        depth_prediction = F.interpolate(
            depth_prediction.unsqueeze(1),
            size=(orig_height, orig_width),
            mode="bicubic",
            align_corners=False
        ).squeeze()
        return depth_prediction.cpu().numpy()

    def process(self, element):
        file_name = "unknown_file"
        image_data = element.data
        
        if element.attributes and 'filename' in element.attributes:
            file_name = element.attributes['filename']
            logging.info(f"Processing image: {file_name}")
            
        try:
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
        except Exception as e:
            logging.error(f"Error opening image: {e}")
            return
            
        orig_width, orig_height = image.size
        logging.info(f"Image dimensions: {orig_width}x{orig_height}")
        
        # Detect pedestrians
        logging.info("Detecting pedestrians...")
        bboxes = self.detect_pedestrians(image)
        logging.info(f"Found {len(bboxes)} pedestrians")
        
        # Estimate depth
        logging.info("Estimating depth...")
        depth_map = self.estimate_depth(image)
        
        result = {
            "file_name": file_name,
            "pedestrians": []
        }
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            x1 = max(0, int(round(x1)))
            y1 = max(0, int(round(y1)))
            x2 = min(orig_width, int(round(x2)))
            y2 = min(orig_height, int(round(y2)))
            if x2 <= x1 or y2 <= y1:
                continue
            region = depth_map[y1:y2, x1:x2]
            avg_depth = float(region.mean())
            result["pedestrians"].append({
                "bbox": [x1, y1, x2, y2],
                "average_depth": avg_depth
            })
        
        logging.info(f"Completed processing {file_name}")
        yield json.dumps(result).encode("utf-8")

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_topic", required=True,
                        help="Input Pub/Sub topic in the format projects/<PROJECT_ID>/topics/<TOPIC_ID>")
    parser.add_argument("--output_topic", required=True,
                        help="Output Pub/Sub topic in the format projects/<PROJECT_ID>/topics/<TOPIC_ID>")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--region", default="us-central1", help="GCP Region for Dataflow job")
    parser.add_argument("--job_name", default="pedestrian-detection", help="Dataflow job name")
    parser.add_argument("--temp_location", required=True, 
                       help="GCS path for temporary files, e.g., gs://your-bucket/temp/")
    parser.add_argument("--staging_location", required=True,
                       help="GCS path for staging, e.g., gs://your-bucket/staging/")
    parser.add_argument("--requirements_file", default="requirements.txt", 
                       help="Path to requirements.txt file for worker dependencies")
    parser.add_argument("--setup_file", default="./setup.py",
                       help="Path to setup.py file")
    parser.add_argument("--worker_container_image", default=None,
                       help="Docker container image for workers")
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).streaming = True
    
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = known_args.project
    google_cloud_options.region = known_args.region
    google_cloud_options.job_name = known_args.job_name
    google_cloud_options.temp_location = known_args.temp_location
    google_cloud_options.staging_location = known_args.staging_location
    
    setup_options = pipeline_options.view_as(SetupOptions)
    setup_options.save_main_session = True
    setup_options.requirements_file = known_args.requirements_file
    setup_options.setup_file = known_args.setup_file
    
    if known_args.worker_container_image:
        worker_options = pipeline_options.view_as(WorkerOptions)
        worker_options.worker_harness_container_image = known_args.worker_container_image
        logging.info(f"Using container image: {known_args.worker_container_image}")
    
    logging.info("Starting pipeline...")
    with beam.Pipeline(options=pipeline_options) as p:
        (p
         | "ReadFromPubSub" >> beam.io.ReadFromPubSub(
             topic=known_args.input_topic,
             with_attributes=True
         )
         | "ProcessImage" >> beam.ParDo(ProcessImageDoFn())
         | "WriteToPubSub" >> beam.io.WriteToPubSub(known_args.output_topic)
        )
    logging.info("Pipeline definition complete")

if __name__ == "__main__":
    run()
    