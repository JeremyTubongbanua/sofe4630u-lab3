#!/usr/bin/env python3
import os
import glob
import argparse
import json
from google.cloud import pubsub_v1
from PIL import Image, ImageDraw
import shutil

files = glob.glob("*.json")
if files:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = files[0]

os.makedirs("./Bounding_Boxed", exist_ok=True)

def draw_bounding_boxes(file_name, pedestrians):
    """Draw bounding boxes on the image and save to output directory."""
    try:
        source_path = os.path.join("./Dataset_Occluded_Pedestrian", file_name)
        if not os.path.exists(source_path):
            print(f"Warning: Source file {source_path} does not exist.")
            return
            
        image = Image.open(source_path)
        draw = ImageDraw.Draw(image)
        
        for pedestrian in pedestrians:
            x1, y1, x2, y2 = pedestrian["bbox"]
            draw.rectangle([(x1, y1), (x2, y2)], outline="red", width=2)
            if "average_depth" in pedestrian:
                depth = pedestrian["average_depth"]
                draw.text((x1, y1-15), f"Depth: {depth:.2f}", fill="red")
                
        output_path = os.path.join("./Bounding_Boxed", file_name)
        image.save(output_path)
        print(f"Saved image with bounding boxes to {output_path}")
        
    except Exception as e:
        print(f"Error processing {file_name}: {e}")

def subscribe(project_id, subscription_id):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    
    def callback(message):
        try:
            decoded = message.data.decode("utf-8")
            print("Received message: {}".format(decoded[:100]))
            
            data = json.loads(decoded)
            file_name = data.get("file_name")
            pedestrians = data.get("pedestrians", [])
            
            if file_name:
                draw_bounding_boxes(file_name, pedestrians)
            
        except json.JSONDecodeError:
            print("Error: Received message is not valid JSON")
        except UnicodeDecodeError:
            print("Received non-text message (raw bytes)")
        except Exception as e:
            print(f"Error processing message: {e}")
        finally:
            message.ack()
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print("Listening for messages on {}...".format(subscription_path))
    print("Images will be saved to ./Bounding_Boxed/")
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        print("Subscription canceled")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="GCP project id")
    parser.add_argument("--subscription", required=True, help="Pub/Sub subscription id")
    args = parser.parse_args()
    subscribe(args.project, args.subscription)

if __name__ == "__main__":
    main()