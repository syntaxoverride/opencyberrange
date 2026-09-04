FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    openssh-server \
    tcpdump \
    python3 \
    python3-pip \
    binutils \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd

# Install tshark non-interactively
RUN echo "wireshark-common wireshark-common/install-setuid boolean false" | debconf-set-selections && \
    apt-get update && apt-get install -y tshark && \
    rm -rf /var/lib/apt/lists/*

# Install scapy for PCAP generation
RUN pip3 install --no-cache-dir scapy

# Create analyst user
RUN useradd -m -s /bin/bash analyst && \
    echo "analyst:T1t4n_4n4lyst#" | chpasswd

# Create evidence directory
RUN mkdir -p /home/analyst/evidence && \
    chown analyst:analyst /home/analyst/evidence

# Generate PCAP during build
COPY generate-pcap.py /tmp/generate-pcap.py
RUN python3 /tmp/generate-pcap.py && \
    chown analyst:analyst /home/analyst/evidence/traffic.pcap && \
    rm /tmp/generate-pcap.py

# SSH config
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
