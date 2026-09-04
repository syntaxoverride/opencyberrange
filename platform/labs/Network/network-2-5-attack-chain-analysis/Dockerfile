FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    wireshark \
    tshark \
    python3 \
    python3-pip \
    tcpdump \
    dnsutils \
    vim \
    nano \
    net-tools \
    iputils-ping \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for PCAP generation
RUN pip3 install scapy

# Create analyst user
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:MediCare2024#' | chpasswd

# Configure SSH
RUN mkdir /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create directory for captures
RUN mkdir -p /home/analyst/captures && \
    chown -R analyst:analyst /home/analyst

# Copy PCAP generation script
COPY generate_attack_pcap.py /tmp/generate_attack_pcap.py

# Generate the multi-stage attack PCAP file
RUN python3 /tmp/generate_attack_pcap.py /home/analyst/captures/full-attack.pcap && \
    chown analyst:analyst /home/analyst/captures/full-attack.pcap && \
    chmod 644 /home/analyst/captures/full-attack.pcap

# Allow analyst to run wireshark without root
RUN groupadd -f wireshark && usermod -a -G wireshark analyst

# Expose SSH port
EXPOSE 22

# Start SSH service
CMD ["/usr/sbin/sshd", "-D"]
