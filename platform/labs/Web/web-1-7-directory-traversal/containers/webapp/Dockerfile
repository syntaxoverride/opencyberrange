FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask

# ── Application ──────────────────────────────────────────────────────
RUN mkdir -p /app/docs /app/config

COPY app.py /app/app.py

# Legitimate documentation files
RUN printf 'Pinnacle Cloud Services. Getting Started Guide\n\
================================================\n\nWelcome to Pinnacle Cloud.\n\n\
1. Create your account at portal.pinnacle-cloud.com\n\
2. Generate API keys in Settings > API Access\n\
3. Install the CLI: pip install pinnacle-cli\n' > /app/docs/getting_started.txt && \
    printf 'Pinnacle Cloud API Reference v3.1\n================================\n\n\
POST /api/v3/compute  . Launch instance\n\
GET  /api/v3/instances. List instances\n\
DELETE /api/v3/instances/:id. Terminate\n' > /app/docs/api_reference.txt && \
    printf 'Release Notes. Q3 2024\n======================\n\n\
- Added GPU instance types\n- Improved dashboard performance\n- Fixed billing edge cases\n' > /app/docs/release_notes.txt && \
    printf 'Security Best Practices\n======================\n\n\
- Rotate API keys every 90 days\n- Enable MFA on all accounts\n- Use VPC for production workloads\n' > /app/docs/security_guide.txt

# Token 1. in application config directory
RUN printf '# Pinnacle Cloud internal configuration\napp_version=3.1.7\ntoken=p4th\nregion=us-west-2\n' > /app/config/token.conf

# Token 2. requires full traversal to /root
RUN printf 'tr4v3rs3d\n' > /root/flag.txt && chmod 644 /root/flag.txt

WORKDIR /app
EXPOSE 80
CMD ["python3", "app.py"]
