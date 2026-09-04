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

# -- Analyst user --------------------------------------------------------------
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:H0r1z0n_S0C#' | chpasswd && \
    usermod -aG wireshark analyst

# -- SSH setup -----------------------------------------------------------------
RUN mkdir -p /run/sshd

# -- Generate evidence PCAP ----------------------------------------------------
RUN mkdir -p /home/analyst/evidence
COPY generate-pcap.py /tmp/generate-pcap.py
RUN python3 /tmp/generate-pcap.py && \
    rm /tmp/generate-pcap.py

# -- auth.log. SSH authentication log with correlating timestamps -------------
RUN printf 'Sep 12 14:10:05 horizon-web sshd[4521]: Accepted publickey for deploy from 10.30.1.10 port 49822 ssh2\n\
Sep 12 14:12:18 horizon-web sshd[4587]: Accepted publickey for deploy from 10.30.1.10 port 49901 ssh2\n\
Sep 12 14:15:33 horizon-web sshd[4612]: Accepted password for admin from 10.30.1.20 port 50112 ssh2\n\
Sep 12 14:18:01 horizon-web sshd[4650]: Failed password for root from 10.30.1.105 port 51022 ssh2\n\
Sep 12 14:18:04 horizon-web sshd[4650]: Failed password for root from 10.30.1.105 port 51022 ssh2\n\
Sep 12 14:18:08 horizon-web sshd[4651]: Failed password for admin from 10.30.1.105 port 51023 ssh2\n\
Sep 12 14:18:12 horizon-web sshd[4651]: Failed password for admin from 10.30.1.105 port 51023 ssh2\n\
Sep 12 14:18:19 horizon-web sshd[4652]: Failed password for deploy from 10.30.1.105 port 51024 ssh2\n\
Sep 12 14:18:25 horizon-web sshd[4653]: Failed password for www-data from 10.30.1.105 port 51025 ssh2\n\
Sep 12 14:18:31 horizon-web sshd[4654]: Failed password for postgres from 10.30.1.105 port 51026 ssh2\n\
Sep 12 14:21:33 horizon-web sshd[4680]: Accepted password for jenkins from 10.30.1.105 port 51100 ssh2\n\
Sep 12 14:21:33 horizon-web sshd[4680]: pam_unix(sshd:session): session opened for user jenkins(uid=1003) by (uid=0)\n\
Sep 12 14:25:10 horizon-web sshd[4680]: pam_unix(sshd:session): session closed for user jenkins\n\
Sep 12 14:30:00 horizon-web sshd[4720]: Accepted publickey for deploy from 10.30.1.10 port 50200 ssh2\n' \
    > /home/analyst/evidence/auth.log

# -- access.log. Apache access log with correlating timestamps ----------------
RUN printf '10.30.1.10 - - [12/Sep/2024:14:10:12 +0000] "GET /index.html HTTP/1.1" 200 4521 "-" "Mozilla/5.0 (X11; Linux x86_64)"\n\
10.30.1.10 - - [12/Sep/2024:14:11:05 +0000] "GET /projects/avionics.html HTTP/1.1" 200 8732 "-" "Mozilla/5.0 (X11; Linux x86_64)"\n\
10.30.1.20 - - [12/Sep/2024:14:12:30 +0000] "GET /news.html HTTP/1.1" 200 3210 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"\n\
10.30.1.20 - - [12/Sep/2024:14:14:45 +0000] "GET /engineering/schedule.html HTTP/1.1" 200 5102 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"\n\
10.30.1.10 - - [12/Sep/2024:14:16:00 +0000] "GET /hr/directory.html HTTP/1.1" 200 2890 "-" "Mozilla/5.0 (X11; Linux x86_64)"\n\
10.30.1.10 - - [12/Sep/2024:14:18:22 +0000] "GET /it/status.html HTTP/1.1" 200 1580 "-" "Mozilla/5.0 (X11; Linux x86_64)"\n\
10.30.1.105 - - [12/Sep/2024:14:22:15 +0000] "POST /upload HTTP/1.1" 200 89 "-" "curl/7.88.1"\n\
10.30.1.105 - - [12/Sep/2024:14:22:45 +0000] "GET /downloads/classified_plans.tar.gz HTTP/1.1" 200 48372816 "-" "curl/7.88.1"\n\
10.30.1.20 - - [12/Sep/2024:14:28:10 +0000] "GET /news.html HTTP/1.1" 200 3210 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"\n\
10.30.1.10 - - [12/Sep/2024:14:30:05 +0000] "GET /hr/timesheet.html HTTP/1.1" 200 4100 "-" "Mozilla/5.0 (X11; Linux x86_64)"\n' \
    > /home/analyst/evidence/access.log

# -- case_brief.txt. incident briefing document -------------------------------
RUN printf '══════════════════════════════════════════════════════════════\n\
  HORIZON AEROSPACE. INCIDENT RESPONSE CASE #IR-2024-0912\n\
══════════════════════════════════════════════════════════════\n\
\n\
Subject:     Suspected intrusion and data exfiltration\n\
Priority:    CRITICAL\n\
Assigned to: SOC Analyst (you)\n\
Date:        2024-09-12\n\
\n\
SUMMARY:\n\
  Multiple detection systems flagged coordinated suspicious activity\n\
  between 14:18 and 14:25 UTC. The IDS recorded SSH brute-force\n\
  attempts followed by successful authentication, suspicious HTTP\n\
  POST requests, outbound FTP transfers to an external IP, and\n\
  DNS queries to a known-bad domain.\n\
\n\
EVIDENCE:\n\
  /home/analyst/evidence/capture.pcap  . network traffic capture\n\
  /home/analyst/evidence/auth.log      . SSH authentication log\n\
  /home/analyst/evidence/access.log    . Apache web server access log\n\
\n\
YOUR OBJECTIVES:\n\
  1. Correlate timestamps across all three evidence sources\n\
  2. Identify the attacker IP address (appears in all three logs)\n\
  3. Determine which user account was compromised (auth.log)\n\
  4. Identify what file was exfiltrated (access.log)\n\
  5. Extract three IOC tokens from the PCAP traffic:\n\
     - Token 1: found in an HTTP POST body (look for token= parameter)\n\
     - Token 2: found in an FTP PASS command\n\
     - Token 3: found as a DNS subdomain label in exfil queries\n\
  6. Assemble flag as: OCR{token1_token2_token3}\n\
\n\
NETWORK CONTEXT:\n\
  10.30.1.0/24  . Internal server subnet\n\
  10.30.1.2     . Internal DNS resolver\n\
  10.30.1.10    . Operations workstation (authorized)\n\
  10.30.1.20    . Engineering workstation (authorized)\n\
  10.30.1.50    . Web server (intranet.horizon-aero.local)\n\
  10.30.1.105   . Unknown / suspicious source\n\
  203.0.113.x   . External (suspicious)\n\
  185.199.x.x   . External (suspicious)\n\
\n\
CORRELATION HINTS:\n\
  - SSH brute-force started at 14:18 from the attacker IP\n\
  - Successful SSH login at 14:21:33 (which account?)\n\
  - HTTP POST at 14:22:15 (matches PCAP timing)\n\
  - File download at 14:22:45 (what file?)\n\
  - FTP and DNS exfil followed shortly after\n\
\n\
TOOLS AVAILABLE:\n\
  tcpdump, tshark, python3/scapy, grep, jq, strings\n\
\n\
══════════════════════════════════════════════════════════════\n' \
    > /home/analyst/evidence/case_brief.txt

# -- Set ownership and permissions ---------------------------------------------
RUN chown -R analyst:analyst /home/analyst/evidence && \
    chmod 644 /home/analyst/evidence/*

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
