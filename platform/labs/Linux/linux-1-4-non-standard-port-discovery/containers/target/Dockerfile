FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install SSH and Apache
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    apache2 \
    && rm -rf /var/lib/apt/lists/*

# Create SSH directory and generate host keys
RUN mkdir -p /var/run/sshd && \
    ssh-keygen -A

# Create a non-root user for SSH access
RUN useradd -m -s /bin/bash techstart && \
    echo "techstart:TechStart2024#" | chpasswd

# Create custom sshd_config with port 2222
# Remove any existing Port lines and add Port 2222
RUN sed -i '/^Port /d' /etc/ssh/sshd_config && \
    sed -i '/^#Port /d' /etc/ssh/sshd_config && \
    echo "Port 22222" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config && \
    /usr/sbin/sshd -t && \
    grep "Port 22222" /etc/ssh/sshd_config

# Put the flag in the user's home directory
RUN echo "OCR{n0n_st4nd4rd}" > /home/techstart/flag.txt && \
    chown techstart:techstart /home/techstart/flag.txt && \
    chmod 644 /home/techstart/flag.txt

# Configure Apache to run on port 8080 (non-standard)
RUN sed -i 's/^Listen 80/Listen 34567/' /etc/apache2/ports.conf && \
    sed -i 's/<VirtualHost \*:80>/<VirtualHost *:34567>/' /etc/apache2/sites-available/000-default.conf && \
    grep -q "^Listen 34567" /etc/apache2/ports.conf || echo "Listen 34567" >> /etc/apache2/ports.conf

# Copy engineering demo page with SSH credentials
COPY index.html /var/www/html/index.html

# Create startup script
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'mkdir -p /var/run/sshd' >> /start.sh && \
    echo 'chmod 755 /var/run/sshd' >> /start.sh && \
    echo '/usr/sbin/sshd' >> /start.sh && \
    echo 'apache2ctl -D FOREGROUND' >> /start.sh && \
    chmod +x /start.sh

EXPOSE 34567 22222

CMD ["/start.sh"]
