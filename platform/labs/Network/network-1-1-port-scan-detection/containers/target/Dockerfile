FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Create directory for logs
RUN mkdir -p /var/www/html

# Create log generation script
COPY generate_logs.py /opt/generate_logs.py
RUN chmod +x /opt/generate_logs.py

# Generate the firewall logs
RUN python3 /opt/generate_logs.py > /var/www/html/firewall.log

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
RUN echo "OCR{p0rt_sc4n_d3t3ct3d}" > /root/flag.txt

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
