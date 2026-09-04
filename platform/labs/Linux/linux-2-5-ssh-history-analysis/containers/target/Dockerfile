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
RUN useradd -m -s /bin/bash developer && \
    echo 'developer:DevAccess2024#' | chpasswd

# Create bash history with flag leaked in commands
RUN mkdir -p /home/developer && \
    echo 'ls -la\ncd /opt/app\ncat config.yml\ncurl -H "Authorization: Bearer OCR{h1st0ry_l34k}" https://api.internal/status\npython3 deploy.py\nexit' > /home/developer/.bash_history && \
    chown developer:developer /home/developer/.bash_history

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
