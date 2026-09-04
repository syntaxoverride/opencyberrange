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

# Create user with password
RUN useradd -m -s /bin/bash financecorp && \
    echo 'financecorp:Welcome2024#' | chpasswd

# Place flag in MOTD and user home
RUN echo 'Welcome to FinanceCorp Server\nSecurity Assessment Flag: OCR{m0td_1nf0}' > /etc/motd
RUN echo 'OCR{m0td_1nf0}' > /home/financecorp/flag.txt && \
    chown financecorp:financecorp /home/financecorp/flag.txt

EXPOSE 22

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
