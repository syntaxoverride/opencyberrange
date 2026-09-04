FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# ── API application ─────────────────────────────────────────────────
RUN mkdir -p /opt/meridian/core-api

COPY api.py /opt/meridian/core-api/api.py
RUN chmod +x /opt/meridian/core-api/api.py

EXPOSE 8080
CMD ["python3", "/opt/meridian/core-api/api.py"]
