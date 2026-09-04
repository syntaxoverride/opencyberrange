FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openssl \
    john \
    vim \
    nano \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── Force SHA-512 for any future password changes and accept $6$ via PAM
RUN sed -i 's/^ENCRYPT_METHOD.*/ENCRYPT_METHOD SHA512/' /etc/login.defs && \
    grep -q '^ENCRYPT_METHOD' /etc/login.defs || echo 'ENCRYPT_METHOD SHA512' >> /etc/login.defs

# ── Users (pre-compute $6$ SHA-512 hashes via openssl; Ubuntu's default
#    yescrypt is not auto-detected by john and is prohibitively slow for
#    a 50-minute lab, so we explicitly set SHA-512 crypt hashes.) ──────
# operator. initial access for the student ("operator" group pre-exists on Ubuntu)
RUN useradd -m -s /bin/bash -g operator -p "$(openssl passwd -6 'Bl4ckr0ck_0ps#')" operator && \
    useradd -m -s /bin/bash -p "$(openssl passwd -6 'security')" engineer && \
    useradd -m -s /bin/bash -p "$(openssl passwd -6 'Bl4ckr0ck_D3v#')" devops

# ── Exposed shadow backup (the vulnerability) ────────────────────────
RUN mkdir -p /opt/blackrock/backups && \
    cp /etc/shadow /opt/blackrock/backups/shadow.bak && \
    cp /etc/passwd /opt/blackrock/backups/passwd.bak && \
    chmod 644 /opt/blackrock/backups/shadow.bak && \
    chmod 644 /opt/blackrock/backups/passwd.bak

# Token 1. in the backup directory
RUN printf 'h4sh_r3l4y\n' > /opt/blackrock/backups/assessment_marker.txt && \
    chmod 644 /opt/blackrock/backups/assessment_marker.txt

# Backup script (context for why the files are there)
RUN printf '#!/bin/bash\n# Nightly backup. configured by former sysadmin\n\
cp /etc/shadow /opt/blackrock/backups/shadow.bak\n\
cp /etc/passwd /opt/blackrock/backups/passwd.bak\n\
echo "Backup completed: $(date)"\n' > /opt/blackrock/backups/backup.sh && \
    chmod 755 /opt/blackrock/backups/backup.sh

# ── Engineer's secrets file (credential relay) ───────────────────────
RUN printf '=== Blackrock Dynamics. Internal Credentials ===\n\
\n\
DevOps Account Credentials\n\
--------------------------\n\
Service:  SSH / deployment access\n\
Username: devops\n\
Password: Bl4ckr0ck_D3v#\n\
\n\
Note: This account has access to the deployment pipeline.\n\
Token hint: the second part of the assessment marker is in the devops home dir.\n' > /home/engineer/secrets.txt && \
    chown engineer:engineer /home/engineer/secrets.txt && \
    chmod 640 /home/engineer/secrets.txt

# ── Token 2 / Flag. in devops home (readable only by devops) ────────
RUN printf 'ch41n\n' > /home/devops/flag.txt && \
    chown devops:devops /home/devops/flag.txt && \
    chmod 600 /home/devops/flag.txt

# ── Realistic flavor ─────────────────────────────────────────────────
RUN printf 'Blackrock Dynamics. Internal Server (blackrock-srv01)\n\
Last patched: 2024-09-10\n\
Contact: marcus.webb@blackrock-dynamics.com\n\
Note: Backup script disabled per ticket SEC-4102, files pending cleanup\n' > /etc/motd

# Operator notes (flavor text)
RUN printf 'Operator workstation notes:\n\
- System monitoring dashboard: http://monitor.blackrock.local:8080\n\
- Backup dir is at /opt/blackrock/backups (read-only for operators)\n\
- Contact infrastructure lead for elevated access\n' > /home/operator/notes.txt && \
    chown operator:operator /home/operator/notes.txt

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22
CMD ["/start.sh"]
