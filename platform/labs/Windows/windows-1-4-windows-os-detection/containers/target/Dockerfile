FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y samba nginx && rm -rf /var/lib/apt/lists/*

# Configure Samba - flag is embedded in the server string that shows during enumeration
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = FINANCECORP" >> /etc/samba/smb.conf && \
    echo "server string = Windows Server 2019 - Flag: OCR{0s_d3t3ct10n}" >> /etc/samba/smb.conf && \
    echo "netbios name = WIN-FINANCE01" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "log level = 0" >> /etc/samba/smb.conf && \
    echo "log file = /dev/null" >> /etc/samba/smb.conf

# Configure nginx with flag
RUN echo "OCR{0s_d3t3ct10n}" > /var/www/html/flag.txt && \
    echo 'user www-data;' > /etc/nginx/nginx.conf && \
    echo 'worker_processes auto;' >> /etc/nginx/nginx.conf && \
    echo 'pid /run/nginx.pid;' >> /etc/nginx/nginx.conf && \
    echo 'events { worker_connections 768; }' >> /etc/nginx/nginx.conf && \
    echo 'http {' >> /etc/nginx/nginx.conf && \
    echo '  sendfile on;' >> /etc/nginx/nginx.conf && \
    echo '  include /etc/nginx/mime.types;' >> /etc/nginx/nginx.conf && \
    echo '  default_type application/octet-stream;' >> /etc/nginx/nginx.conf && \
    echo '  server {' >> /etc/nginx/nginx.conf && \
    echo '    listen 80 default_server;' >> /etc/nginx/nginx.conf && \
    echo '    root /var/www/html;' >> /etc/nginx/nginx.conf && \
    echo '    location / { try_files $uri $uri/ =404; autoindex on; }' >> /etc/nginx/nginx.conf && \
    echo '  }' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf

EXPOSE 445 139 80

CMD service smbd start && nginx -g "daemon off;"
