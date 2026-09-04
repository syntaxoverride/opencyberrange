FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip dnsutils \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask

RUN mkdir -p /app /opt/truenorth/hidden_config

COPY app.py /app/app.py

# Token 1. hidden config directory
RUN printf 'f1lt3r_byp4ss\n' > /opt/truenorth/hidden_config/token1.txt

# Token 2. root flag
RUN printf 'pwn3d\n' > /root/flag.txt && chmod 644 /root/flag.txt

WORKDIR /app
EXPOSE 80
CMD ["python3", "app.py"]
