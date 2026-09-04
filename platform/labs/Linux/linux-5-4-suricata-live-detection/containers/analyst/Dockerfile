FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    suricata \
    openssh-server \
    nginx \
    tcpdump \
    jq \
    sudo \
    procps \
    nano \
    && rm -rf /var/lib/apt/lists/*

# ── Analyst user (student SSH access) ────────────────────────────────
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:S3nt1n3l_S0C#' | chpasswd && \
    echo 'analyst ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── Suricata configuration ──────────────────────────────────────────
RUN mkdir -p /var/run/suricata /var/log/suricata /etc/suricata/rules

COPY suricata.yaml /etc/suricata/suricata.yaml

# Empty local.rules. student writes detection rules here
RUN touch /etc/suricata/rules/local.rules && \
    chown analyst:analyst /etc/suricata/rules/local.rules

# Ensure classification and reference configs exist (needed by Suricata)
RUN test -f /etc/suricata/classification.config || \
    touch /etc/suricata/classification.config && \
    test -f /etc/suricata/reference.config || \
    touch /etc/suricata/reference.config

# ── Honeypot nginx (accepts attacker traffic for Suricata to see) ────
COPY nginx.conf /etc/nginx/nginx.conf

# ── Validation script ───────────────────────────────────────────────
COPY validate-flag.sh /usr/local/bin/validate-flag
RUN chmod +x /usr/local/bin/validate-flag

# ── Startup ─────────────────────────────────────────────────────────
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22 80

CMD ["/start.sh"]
