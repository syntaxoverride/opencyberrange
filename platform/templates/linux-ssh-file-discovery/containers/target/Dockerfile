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

# Base user. The entrypoint renames/recreates this from CRED_ssh-user_* at spawn,
# but the baked default keeps the image runnable standalone.
RUN useradd -m -s /bin/bash webadmin && \
    echo 'webadmin:WebServer2024#' | chpasswd

# Web directory structure. The flag file is (re)written by the entrypoint from
# the FLAG env var; this baked copy is the standalone fallback.
RUN mkdir -p /var/www/html/backups && \
    echo '<html><body>Corporate Web Portal</body></html>' > /var/www/html/index.html

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
