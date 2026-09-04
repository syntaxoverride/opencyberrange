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

# Create multiple users for discovery exercise
RUN useradd -m -s /bin/bash jmitchell && \
    echo 'jmitchell:Finance2024#' | chpasswd && \
    useradd -m -s /bin/bash admin && \
    echo 'admin:AdminSecure99#' | chpasswd && \
    useradd -m -s /bin/bash dbbackup && \
    echo 'dbbackup:BackupPass2024#' | chpasswd && \
    useradd -m -s /bin/bash webmaster && \
    echo 'webmaster:WebM4ster#' | chpasswd

# Place flag in user_info.txt
RUN echo 'FinanceCorp User Directory\nFlag: OCR{us3r_d1sc0v3ry}' > /home/jmitchell/user_info.txt && \
    chown jmitchell:jmitchell /home/jmitchell/user_info.txt

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
