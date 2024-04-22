FROM python:3.11

WORKDIR /app
COPY . /app

RUN apt-get update && \
    apt-get install -y python3-libtorrent && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "egitorrent.py"]
