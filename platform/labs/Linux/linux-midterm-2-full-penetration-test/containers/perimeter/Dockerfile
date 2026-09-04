FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask

# ── Web application with command injection ───────────────────────────
RUN mkdir -p /var/www/nexus-app /opt/nexus/assessment

RUN printf 'APP_NAME=Nexus Dynamics Platform\n\
APP_ENV=production\n\
API_VERSION=4.1.2\n\
\n\
CORE_SSH_HOST=nexus-core\n\
CORE_SSH_USER=deploy\n\
CORE_SSH_PASS=N3xus_D3pl0y#\n\
CORE_SSH_PORT=22\n\
\n\
DB_HOST=db.internal.nexus\n\
DB_NAME=nexus_prod\n' > /var/www/nexus-app/.env

# Marker 1
RUN printf 'br34ch\n' > /opt/nexus/assessment/marker1.txt

COPY app.py /var/www/nexus-app/app.py

WORKDIR /var/www/nexus-app
EXPOSE 80
CMD ["python3", "app.py"]
