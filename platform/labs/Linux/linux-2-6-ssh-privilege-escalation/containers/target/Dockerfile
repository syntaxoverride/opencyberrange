FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir -p /run/sshd && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'UseDNS no' >> /etc/ssh/sshd_config

# Force SHA-512 so /etc/shadow contains $6$ hashes (workbook demonstrates john cracking)
RUN sed -i 's/^ENCRYPT_METHOD.*/ENCRYPT_METHOD SHA512/' /etc/login.defs && \
    grep -q '^ENCRYPT_METHOD' /etc/login.defs || echo 'ENCRYPT_METHOD SHA512' >> /etc/login.defs

# Create user with limited sudo access (backup user may already exist in base image)
RUN userdel -r backup 2>/dev/null; \
    useradd -m -s /bin/bash -p "$(openssl passwd -6 'Backup2024#')" backup

# Install sudo
RUN apt-get update && apt-get install -y --no-install-recommends sudo && rm -rf /var/lib/apt/lists/*

# Grant sudo cat without password
RUN echo 'backup ALL=(ALL) NOPASSWD: /usr/bin/cat' > /etc/sudoers.d/backup && \
    chmod 440 /etc/sudoers.d/backup

# Place flag in root-only file
RUN echo 'OCR{sud0_3sc}' > /root/flag.txt && \
    chmod 600 /root/flag.txt

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
