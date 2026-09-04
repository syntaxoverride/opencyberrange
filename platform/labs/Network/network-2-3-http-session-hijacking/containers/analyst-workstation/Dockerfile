FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    python3 \
    python3-pip \
    wireshark \
    tshark \
    tcpdump \
    net-tools \
    iputils-ping \
    vim \
    nano \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for PCAP generation
RUN pip3 install scapy

# Create analyst user
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:MediCare2024#' | chpasswd && \
    usermod -aG sudo analyst

# Create captures directory
RUN mkdir -p /home/analyst/captures && \
    chown -R analyst:analyst /home/analyst/captures

# Copy PCAP generation script
COPY generate_http_pcap.py /tmp/generate_http_pcap.py

# Generate the PCAP file
RUN python3 /tmp/generate_http_pcap.py /home/analyst/captures/session-hijack.pcap && \
    chown analyst:analyst /home/analyst/captures/session-hijack.pcap && \
    chmod 644 /home/analyst/captures/session-hijack.pcap

# Configure SSH
RUN mkdir /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create a welcome message (only for interactive sessions to avoid SCP issues)
RUN echo '#!/bin/bash\n\
# Only show welcome message for interactive shells (not SCP/SFTP)\n\
if [ -t 0 ]; then\n\
    echo "================================================================="\n\
    echo "  MediCare Health Systems - Network Analysis Station"\n\
    echo "================================================================="\n\
    echo ""\n\
    echo "Welcome, Security Analyst!"\n\
    echo ""\n\
    echo "INCIDENT REPORT:"\n\
    echo "A patient reported unauthorized access to their medical records."\n\
    echo "Session hijacking is suspected. Analyze the packet capture to"\n\
    echo "identify how the attacker gained access."\n\
    echo ""\n\
    echo "Available captures:"\n\
    echo "  - captures/session-hijack.pcap"\n\
    echo ""\n\
    echo "Tools available:"\n\
    echo "  - wireshark (GUI - may need X forwarding)"\n\
    echo "  - tshark (CLI alternative)"\n\
    echo "  - tcpdump"\n\
    echo ""\n\
    echo "Tip: Look for HTTP cookies and session patterns"\n\
    echo "================================================================="\n\
    echo ""\n\
fi' > /home/analyst/.bashrc && \
    chown analyst:analyst /home/analyst/.bashrc

# Expose SSH port
EXPOSE 22

# Start SSH service
CMD ["/usr/sbin/sshd", "-D"]
