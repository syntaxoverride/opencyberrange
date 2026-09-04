FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir -p /run/sshd && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'UseDNS no' >> /etc/ssh/sshd_config

# Create user
RUN useradd -m -s /bin/bash webadmin && \
    echo 'webadmin:WebServer2024#' | chpasswd

# Create web directory structure with flag
RUN mkdir -p /var/www/html/backups && \
    echo '<html><body>FinanceCorp Web Portal</body></html>' > /var/www/html/index.html && \
    echo 'Deployment Notes - v3.2.1\nDeployed: 2024-01-15\nFlag: OCR{f1l3_d1sc0v3ry}' > /var/www/html/backups/deployment_notes.txt

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
