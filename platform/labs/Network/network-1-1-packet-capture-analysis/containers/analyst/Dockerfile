FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Accept wireshark EULA for tshark non-interactive install
RUN echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    tshark \
    tcpdump \
    python3 \
    python3-pip \
    jq \
    net-tools \
    file \
    && rm -rf /var/lib/apt/lists/*

# scapy for PCAP generation (and available for student use)
RUN pip3 install --no-cache-dir scapy

# ── Analyst user ─────────────────────────────────────────────────────
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:Av4l0n_S0C#' | chpasswd && \
    usermod -aG wireshark analyst

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── Generate evidence PCAP ───────────────────────────────────────────
RUN mkdir -p /home/analyst/evidence
COPY generate-pcap.py /tmp/generate-pcap.py
RUN python3 /tmp/generate-pcap.py && \
    rm /tmp/generate-pcap.py && \
    chown -R analyst:analyst /home/analyst/evidence && \
    chmod 644 /home/analyst/evidence/capture.pcap

# ── Case brief for context ──────────────────────────────────────────
RUN printf '══════════════════════════════════════════════════════════════\n\
  AVALON BIOTECH. INCIDENT RESPONSE CASE #IR-2024-0305\n\
══════════════════════════════════════════════════════════════\n\
\n\
Subject:     Suspected data exfiltration. R&D department\n\
Priority:    HIGH\n\
Assigned to: SOC Analyst (you)\n\
Date:        2024-03-05\n\
\n\
SUMMARY:\n\
  SIEM alerts triggered for anomalous outbound connections from\n\
  workstation 10.20.1.105 (Mark Sullivan, Research Associate).\n\
  Multiple external IPs contacted over HTTP, FTP, and DNS.\n\
\n\
EVIDENCE:\n\
  /home/analyst/evidence/capture.pcap\n\
  - 5-minute network capture from the suspect workstation\n\
  - Captured by span port on core switch SW-R&D-01\n\
\n\
OBJECTIVES:\n\
  1. Identify all external connections from 10.20.1.105\n\
  2. Extract any credentials or authentication tokens used\n\
  3. Determine what data was exfiltrated and via what method\n\
  4. Extract the three IOC markers from the traffic\n\
  5. Assemble flag as: OCR{ioc1_ioc2_ioc3}\n\
\n\
NETWORK CONTEXT:\n\
  10.20.1.0/24 . R&D department subnet\n\
  10.20.1.2    . Internal DNS resolver\n\
  10.20.1.10   . Internal web server (intranet.avalon.local)\n\
  10.20.1.105  . Suspect workstation\n\
  198.51.100.x . External (suspicious)\n\
  203.0.113.x  . External (suspicious)\n\
  185.199.x.x  . External (suspicious)\n\
\n\
TOOLS AVAILABLE:\n\
  tcpdump, tshark, python3/scapy, strings, grep\n\
\n\
══════════════════════════════════════════════════════════════\n' \
    > /home/analyst/evidence/case_brief.txt && \
    chown analyst:analyst /home/analyst/evidence/case_brief.txt

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
