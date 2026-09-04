FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install scapy for PCAP generation
RUN pip3 install scapy

# Create directory for served files
RUN mkdir -p /var/www/html

# Copy PCAP generation script
COPY pcap_generator.py /opt/pcap_generator.py
RUN chmod +x /opt/pcap_generator.py

# Generate the PCAP file
RUN python3 /opt/pcap_generator.py /var/www/html/capture.pcap

# Configure nginx to serve the PCAP file
RUN echo 'server {' > /etc/nginx/sites-available/default && \
    echo '    listen 80 default_server;' >> /etc/nginx/sites-available/default && \
    echo '    root /var/www/html;' >> /etc/nginx/sites-available/default && \
    echo '    location / {' >> /etc/nginx/sites-available/default && \
    echo '        autoindex on;' >> /etc/nginx/sites-available/default && \
    echo '        add_header Content-Type application/vnd.tcpdump.pcap;' >> /etc/nginx/sites-available/default && \
    echo '    }' >> /etc/nginx/sites-available/default && \
    echo '}' >> /etc/nginx/sites-available/default

# Create flag file
RUN echo "OCR{http_cr3d3nt14ls}" > /root/flag.txt

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
