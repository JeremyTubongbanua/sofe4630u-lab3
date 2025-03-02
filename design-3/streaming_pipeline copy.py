#!/usr/bin/env python3
import argparse
import io
import json
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
import torch
import torchvision
import numpy as np
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F
import glob
import os

files=glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=files[0];

class ProcessImageDoFn(beam.DoFn):
    def setup(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.detection_model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
        self.detection_model.to(self.device)
        self.detection_model.eval()
        self.midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
        self.midas.to(self.device)
        self.midas.eval()
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        self.midas_transform = midas_transforms.small_transform

    def detect_pedestrians(self, image):
        transform = T.ToTensor()
        image_tensor = transform(image).to(self.device)
        with torch.no_grad():
            detections = self.detection_model([image_tensor])[0]
        pedestrian_bboxes = []
        for box, label, score in zip(detections["boxes"], detections["labels"], detections["scores"]):
            if label.item() == 1 and score.item() >= 0.5:
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
        try:
            image = Image.open(io.BytesIO(element)).convert("RGB")
        except Exception as e:
            logging.error("Error reading image: %s", e)
            return
        orig_width, orig_height = image.size
        bboxes = self.detect_pedestrians(image)
        depth_map = self.estimate_depth(image)
        result = {"pedestrians": []}
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
        yield json.dumps(result).encode("utf-8")

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_topic", required=True,
                        help="Input Pub/Sub topic in the format projects/<PROJECT_ID>/topics/<TOPIC_ID>")
    parser.add_argument("--output_topic", required=True,
                        help="Output Pub/Sub topic in the format projects/<PROJECT_ID>/topics/<TOPIC_ID>")
    parser.add_argument("--runner", default="DirectRunner", help="Pipeline runner")
    known_args, pipeline_args = parser.parse_known_args(argv)
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).streaming = True
    with beam.Pipeline(options=pipeline_options) as p:
        (p
         | "ReadFromPubSub" >> beam.io.ReadFromPubSub(topic=known_args.input_topic)
         | "ProcessImage" >> beam.ParDo(ProcessImageDoFn())
         | "WriteToPubSub" >> beam.io.WriteToPubSub(known_args.output_topic)
        )

if __name__ == "__main__":
    run()
