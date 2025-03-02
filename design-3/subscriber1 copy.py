#!/usr/bin/env python3
import os
import glob
import argparse
from google.cloud import pubsub_v1

# Search the current directory for a JSON file (typically the service account key)
files = glob.glob("*.json")
if files:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = files[0]

def subscribe(project_id, subscription_id):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    
    def callback(message):
        try:
            decoded = message.data.decode("utf-8")
            print("Received message: {}".format(decoded[:100]))
        except UnicodeDecodeError:
            print("Received non-text message (raw bytes): {}".format(message.data[:100]))
        message.ack()
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print("Listening for messages on {}...".format(subscription_path))
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="GCP project id")
    parser.add_argument("--subscription", required=True, help="Pub/Sub subscription id")
    args = parser.parse_args()
    subscribe(args.project, args.subscription)

if __name__ == "__main__":
    main()
