#!/usr/bin/env python3
import time
from google.cloud import pubsub_v1

files=glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=files[0];

project_id = "sofe4630u-449800"
subscription_id = "design3-sub"
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

def callback(message):
    print("Received message: {}".format(message.data.decode("utf-8")))
    message.ack()

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
print("Listening for messages on {}...".format(subscription_path))
try:
    streaming_pull_future.result()
except KeyboardInterrupt:
    streaming_pull_future.cancel()
