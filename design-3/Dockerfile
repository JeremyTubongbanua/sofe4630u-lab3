FROM python:3.9-slim

WORKDIR /app

COPY .  .

RUN apt-get update && apt-get install -y gcc python3-dev

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "pedestrian_detection_dataflow.py"]
