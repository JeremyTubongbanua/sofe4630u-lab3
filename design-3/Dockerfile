FROM python:3.8-slim
RUN apt-get update && apt-get install -y build-essential
RUN pip install --upgrade pip
RUN pip install apache-beam[gcp] torch torchvision pillow google-cloud-pubsub
COPY dataflow_pipeline.py /app/dataflow_pipeline.py
WORKDIR /app
ENTRYPOINT ["python", "dataflow_pipeline.py"]
