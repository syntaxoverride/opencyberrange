FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask

RUN mkdir -p /app
COPY app.py /app/app.py

WORKDIR /app
EXPOSE 80
CMD ["python3", "app.py"]
