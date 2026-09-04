FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx python3 \
    && rm -rf /var/lib/apt/lists/*

# Copy static HTML assets
COPY html/ /var/www/html/

# Nginx config: default location without autoindex, /internal/ with autoindex
RUN echo 'user www-data;' > /etc/nginx/nginx.conf && \
    echo 'worker_processes auto;' >> /etc/nginx/nginx.conf && \
    echo 'pid /run/nginx.pid;' >> /etc/nginx/nginx.conf && \
    echo 'events { worker_connections 768; }' >> /etc/nginx/nginx.conf && \
    echo 'http {' >> /etc/nginx/nginx.conf && \
    echo '  sendfile on;' >> /etc/nginx/nginx.conf && \
    echo '  tcp_nopush on;' >> /etc/nginx/nginx.conf && \
    echo '  types_hash_max_size 2048;' >> /etc/nginx/nginx.conf && \
    echo '  include /etc/nginx/mime.types;' >> /etc/nginx/nginx.conf && \
    echo '  default_type application/octet-stream;' >> /etc/nginx/nginx.conf && \
    echo '  access_log /var/log/nginx/access.log;' >> /etc/nginx/nginx.conf && \
    echo '  error_log /var/log/nginx/error.log;' >> /etc/nginx/nginx.conf && \
    echo '  server {' >> /etc/nginx/nginx.conf && \
    echo '    listen 80 default_server;' >> /etc/nginx/nginx.conf && \
    echo '    root /var/www/html;' >> /etc/nginx/nginx.conf && \
    echo '    index index.html index.htm;' >> /etc/nginx/nginx.conf && \
    echo '    location / { try_files $uri $uri/ =404; }' >> /etc/nginx/nginx.conf && \
    echo '    location /internal/ { autoindex on; try_files $uri $uri/ =404; }' >> /etc/nginx/nginx.conf && \
    echo '  }' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf

EXPOSE 80 8080

# Run nginx in background, then Python http.server on 8080 for dev docs (foreground keeps container alive)
CMD nginx -g "daemon off;" & python3 -m http.server 8080 --directory /var/www/html/dev --bind 0.0.0.0
