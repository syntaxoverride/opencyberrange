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
RUN useradd -m -s /bin/bash sysadmin && \
    echo 'sysadmin:SysAdmin2024#' | chpasswd

# Set flag as environment variable (in profile so it's available on SSH login)
RUN echo 'export SECURITY_ASSESSMENT_FLAG="OCR{cmd_3x3c}"' >> /home/sysadmin/.bashrc && \
    echo 'export SECURITY_ASSESSMENT_FLAG="OCR{cmd_3x3c}"' >> /etc/environment

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
