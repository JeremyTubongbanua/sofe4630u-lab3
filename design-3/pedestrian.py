#!/usr/bin/env python3
import argparse
import json
import torch
import torchvision
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F
import numpy as np
import glob

files=glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=files[0];

def load_detection_model(device):
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
    model.to(device)
    model.eval()
    return model

def load_midas_model(device):
    midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
    midas.to(device)
    midas.eval()
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    transform = midas_transforms.small_transform
    return midas, transform

def detect_pedestrians(image, detection_model, device, score_thresh=0.5):
    transform = T.ToTensor()
    image_tensor = transform(image).to(device)
    with torch.no_grad():
        detections = detection_model([image_tensor])[0]
    pedestrian_bboxes = []
    for box, label, score in zip(detections["boxes"], detections["labels"], detections["scores"]):
        if label.item() == 1 and score.item() >= score_thresh:
            pedestrian_bboxes.append(box.cpu().numpy().tolist())
    return pedestrian_bboxes

def estimate_depth(image, midas, midas_transform, device):
    image_np = np.array(image)
    transformed = midas_transform(image_np)
    if isinstance(transformed, dict) and "image" in transformed:
        input_depth = transformed["image"]
    else:
        input_depth = transformed
    if not torch.is_tensor(input_depth):
        input_depth = torch.from_numpy(input_depth)
    input_depth = input_depth.to(device)
    if input_depth.ndim == 3:
        input_depth = input_depth.unsqueeze(0)
    with torch.no_grad():
        depth_prediction = midas(input_depth)
    orig_width, orig_height = image.size
    depth_prediction = F.interpolate(
        depth_prediction.unsqueeze(1),
        size=(orig_height, orig_width),
        mode="bicubic",
        align_corners=False,
    ).squeeze()
    depth_map = depth_prediction.cpu().numpy()
    return depth_map

def main():
    parser = argparse.ArgumentParser(description="Detect pedestrians and estimate their depth.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to the input image file.")
    parser.add_argument("--output_file", type=str, required=True, help="Path to the output JSON file.")
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    image = Image.open(args.input_file).convert("RGB")
    orig_width, orig_height = image.size
    detection_model = load_detection_model(device)
    midas, midas_transform = load_midas_model(device)
    pedestrian_bboxes = detect_pedestrians(image, detection_model, device, score_thresh=0.5)
    depth_map = estimate_depth(image, midas, midas_transform, device)
    results = {"pedestrians": []}
    for bbox in pedestrian_bboxes:
        x1, y1, x2, y2 = bbox
        x1 = max(0, int(round(x1)))
        y1 = max(0, int(round(y1)))
        x2 = min(orig_width, int(round(x2)))
        y2 = min(orig_height, int(round(y2)))
        if x2 <= x1 or y2 <= y1:
            continue
        region = depth_map[y1:y2, x1:x2]
        avg_depth = float(region.mean())
        results["pedestrians"].append({
            "bbox": [x1, y1, x2, y2],
            "average_depth": avg_depth
        })
    with open(args.output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Processed {len(results['pedestrians'])} pedestrians. Results saved to {args.output_file}")

if __name__ == "__main__":
    main()
