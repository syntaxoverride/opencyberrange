FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openssl \
    john \
    wordlists \
    && rm -rf /var/lib/apt/lists/*

# ── Wordlist ──────────────────────────────────────────────────────────
RUN gunzip /usr/share/wordlists/rockyou.txt.gz || true

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── Force SHA-512 for any future password changes and accept $6$ via PAM
RUN sed -i 's/^ENCRYPT_METHOD.*/ENCRYPT_METHOD SHA512/' /etc/login.defs && \
    grep -q '^ENCRYPT_METHOD' /etc/login.defs || echo 'ENCRYPT_METHOD SHA512' >> /etc/login.defs

# ── Users (pre-compute $6$ SHA-512 hashes via openssl; Kali's default
#    yescrypt is not auto-detected by john and is prohibitively slow for
#    a 45-minute lab, so we explicitly set SHA-512 crypt hashes.) ──────
RUN useradd -m -s /bin/bash -p "$(openssl passwd -6 'Ir0nf0rg3_T3ch#')" technician && \
    useradd -m -s /bin/bash -p "$(openssl passwd -6 'dragon')" sysadmin && \
    useradd -m -s /bin/bash -p "$(openssl passwd -6 'C0mpl3x_P@ssw0rd_2024_N0tCr4ckable#')" webmaster

# ── Misconfigured backup directory (world-readable) ──────────────────
RUN mkdir -p /opt/ironforge/backups && \
    cp /etc/shadow /opt/ironforge/backups/shadow.bak && \
    cp /etc/passwd /opt/ironforge/backups/passwd.bak && \
    chmod 644 /opt/ironforge/backups/shadow.bak && \
    chmod 644 /opt/ironforge/backups/passwd.bak

# Token 1. in the backup directory
RUN printf 'cr4ck3d\n' > /opt/ironforge/backups/assessment_token.txt && \
    chmod 644 /opt/ironforge/backups/assessment_token.txt

# Backup script (context for why the files are there)
RUN printf '#!/bin/bash\n# Nightly backup. configured by former sysadmin\n\
cp /etc/shadow /opt/ironforge/backups/shadow.bak\n\
cp /etc/passwd /opt/ironforge/backups/passwd.bak\n\
echo "Backup completed: $(date)"\n' > /opt/ironforge/backups/backup.sh && \
    chmod 755 /opt/ironforge/backups/backup.sh

# Token 2. in sysadmin's home (accessible after cracking their password)
RUN printf 'h4sh3s\n' > /home/sysadmin/flag.txt && \
    chown sysadmin:sysadmin /home/sysadmin/flag.txt && \
    chmod 600 /home/sysadmin/flag.txt

# Flavor: sysadmin's notes
RUN printf 'Ironforge Hosting. Server Notes\n\
Last patched: 2024-08-15\n\
Backup script: /opt/ironforge/backups/backup.sh\n\
TODO: fix backup permissions (Rachel keeps asking)\n' > /home/sysadmin/notes.txt && \
    chown sysadmin:sysadmin /home/sysadmin/notes.txt

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22
CMD ["/start.sh"]
