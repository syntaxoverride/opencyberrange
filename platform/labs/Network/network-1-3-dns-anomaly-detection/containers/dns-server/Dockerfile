FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Create directory for logs
RUN mkdir -p /var/www/html

# Create DNS log generation script
COPY generate_dns_logs.py /opt/generate_dns_logs.py
RUN chmod +x /opt/generate_dns_logs.py

# Generate the DNS query logs
RUN python3 /opt/generate_dns_logs.py > /var/www/html/dns.log

# Configure nginx to serve logs
RUN echo 'server {' > /etc/nginx/sites-available/default && \
    echo '    listen 80 default_server;' >> /etc/nginx/sites-available/default && \
    echo '    root /var/www/html;' >> /etc/nginx/sites-available/default && \
    echo '    location / {' >> /etc/nginx/sites-available/default && \
    echo '        autoindex on;' >> /etc/nginx/sites-available/default && \
    echo '        add_header Content-Type text/plain;' >> /etc/nginx/sites-available/default && \
    echo '    }' >> /etc/nginx/sites-available/default && \
    echo '}' >> /etc/nginx/sites-available/default

# Create flag file
RUN echo "OCR{dns_3xf1ltr4t10n}" > /root/flag.txt

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
