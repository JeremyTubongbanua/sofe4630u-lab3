#!/usr/bin/env python3
import os
import argparse
from google.cloud import pubsub_v1
import glob
import re

files=glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=files[0];

def natural_sort_key(s):
    """
    Sort strings containing numbers in natural order.
    For example: ["img1.png", "img10.png", "img2.png"] will be sorted as
    ["img1.png", "img2.png", "img10.png"] instead of ASCII order.
    """
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

def publish(project_id, topic_id, folder):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    # Get all PNG files and sort them
    png_files = [f for f in os.listdir(folder) if f.lower().endswith(".png")]
    png_files.sort(key=natural_sort_key)
    
    for filename in png_files:
        filepath = os.path.join(folder, filename)
        with open(filepath, "rb") as f:
            data = f.read()
        future = publisher.publish(topic_path, data, filename=filename)
        print("Published {}: {}".format(filename, future.result()))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="GCP project id")
    parser.add_argument("--topic", required=True, help="Pub/Sub topic id")
    parser.add_argument("--folder", required=True, help="Local folder containing PNG images")
    args = parser.parse_args()
    publish(args.project, args.topic, args.folder)

if __name__ == "__main__":
    main()