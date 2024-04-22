FROM python:3.8

WORKDIR /app
COPY . /app

RUN apt-get update && \
    apt-get install -y build-essential checkinstall libboost-system-dev libboost-python-dev libboost-chrono-dev libboost-random-dev libssl-dev && \
    wget https://github.com/arvidn/libtorrent/releases/download/libtorrent-1_2_14/libtorrent-rasterbar-1.2.14.tar.gz && \
    tar -zxvf libtorrent-rasterbar-1.2.14.tar.gz && \
    cd libtorrent-rasterbar-1.2.14/ && \
    ./configure --enable-python-binding && \
    make && \
    checkinstall && \
    ldconfig && \
    cd ../ && \
    rm -rf libtorrent-rasterbar-1.2.14/ && \
    rm libtorrent-rasterbar-1.2.14.tar.gz && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "egitorrent.py"]
