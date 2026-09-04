FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba xrdp nginx \
    && rm -rf /var/lib/apt/lists/*

# Configure Samba
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = Windows Server" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "[public]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/public" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf

# Create public share directory and flag
RUN mkdir -p /tmp/public && \
    echo "OCR{mult1pl3_p0rts}" > /tmp/public/flag.txt

# Configure xrdp
RUN useradd -m -s /bin/bash rdpuser && echo "rdpuser:password123" | chpasswd
RUN echo "OCR{mult1pl3_p0rts}" > /home/rdpuser/flag.txt

# Configure nginx - replace entire nginx.conf to avoid sites-enabled issues
RUN echo "OCR{mult1pl3_p0rts}" > /var/www/html/flag.txt && \
    echo 'user www-data;' > /etc/nginx/nginx.conf && \
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
    echo '    location / { try_files $uri $uri/ =404; autoindex on; }' >> /etc/nginx/nginx.conf && \
    echo '  }' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf

EXPOSE 445 3389 80

CMD service smbd start && service xrdp start && nginx -g "daemon off;"
