FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server sudo gnupg xxd \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]
RUN mkdir -p /run/sshd

# ── Operator user with sudo ──────────────────────────────────────────
RUN useradd -m -s /bin/bash -g operator operator && \
    echo 'operator:0bs1d14n_0ps#' | chpasswd && \
    echo 'operator ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# ═══════════════════════════════════════════════════════════════════════
# Token 1: Base64-encoded export file
# ═══════════════════════════════════════════════════════════════════════
RUN mkdir -p /var/backups/obsidian && \
    printf 'Obsidian Analytics. Quarterly Data Export\n\
Report ID: OA-2024-Q3-7841\n\
Generated: 2024-09-15 03:00:00 UTC\n\
Classification: INTERNAL\n\
\n\
export_format: csv\n\
record_count: 24817\n\
assessment_marker: 3ncrypt\n\
checksum: a4f8e2c19b0d3671\n\
\n\
--- END HEADER ---\n' | base64 > /var/backups/obsidian/export.b64

# ═══════════════════════════════════════════════════════════════════════
# Token 2: GPG symmetrically encrypted archive
# ═══════════════════════════════════════════════════════════════════════
RUN mkdir -p /opt/obsidian/data && \
    printf '[obsidian-internal]\n\
project: threat_intelligence_feed\n\
version: 3.8.1\n\
status: active\n\
\n\
marker_value=d3c0d3\n\
\n\
database_host: db-prod-01.obsidian.local\n\
database_port: 5432\n\
api_endpoint: https://api.obsidian.local/v2/feeds\n' > /tmp/archive_data.txt && \
    gpg --batch --yes --passphrase '0bs1d14n_Vault#' --symmetric \
        --cipher-algo AES256 -o /opt/obsidian/data/archive.gpg \
        /tmp/archive_data.txt && \
    rm /tmp/archive_data.txt

# ═══════════════════════════════════════════════════════════════════════
# Token 3: Hex-encoded hidden dotfile
# ═══════════════════════════════════════════════════════════════════════
RUN mkdir -p /opt/obsidian/.cache && \
    printf '3xf1l' | xxd -p > /opt/obsidian/.cache/.data_store

# ── Bash history with GPG passphrase breadcrumb ───────────────────────
RUN printf 'cd /opt/obsidian\n\
ls -la\n\
cat /var/log/syslog | tail -50\n\
sudo systemctl status obsidian-feed\n\
gpg --batch --passphrase '\''0bs1d14n_Vault#'\'' -d /opt/obsidian/data/archive.gpg\n\
df -h\n\
sudo netstat -tlnp\n\
exit\n' > /home/operator/.bash_history && \
    chown operator:operator /home/operator/.bash_history && \
    chmod 600 /home/operator/.bash_history

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
