FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    findutils \
    sudo \
    vim \
    nano \
    curl \
    net-tools \
    procps \
    cron \
    gcc \
    make \
    && rm -rf /var/lib/apt/lists/*

# ── Developer user (student SSH access) ──────────────────────────────
RUN useradd -m -s /bin/bash developer && \
    echo 'developer:M3r1d1an_D3v#' | chpasswd

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── Realistic development environment ───────────────────────────────
# Fake project files to make it look like a real build server
RUN mkdir -p /opt/meridian/projects/analytics-engine/src && \
    echo '#!/bin/bash\n# Build script for Meridian Analytics Engine v4.2\necho "Building..."' \
        > /opt/meridian/projects/analytics-engine/build.sh && \
    echo 'DB_HOST=prod-db.meridian.local\nDB_PORT=5432\nAPP_ENV=staging' \
        > /opt/meridian/projects/analytics-engine/.env && \
    echo 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("Meridian Analytics Engine")\n}' \
        > /opt/meridian/projects/analytics-engine/src/main.go && \
    chown -R developer:developer /opt/meridian/projects

# Developer notes (flavor text)
RUN echo 'Meridian Build Server (meridian-build01)\n\
Last patched: 2024-08-22\n\
Contact: riley.park@meridian-data.com\n\
Note: Development tools installed per ticket IT-2847' > /etc/motd

# ── SUID misconfiguration (the vulnerability) ───────────────────────
# "find" with SUID bit. installed per developer request, never audited
RUN chmod u+s /usr/bin/find

# Create a decoy SUID binary that looks interesting but isn't exploitable
RUN echo '#!/bin/bash\necho "Meridian System Status"\necho "Uptime: $(uptime -p)"\necho "Disk: $(df -h / | tail -1)"' \
        > /usr/local/bin/statuscheck && \
    chmod 4755 /usr/local/bin/statuscheck

# ── Flag ─────────────────────────────────────────────────────────────
RUN echo 'OCR{su1d_pr1v3sc_r00t3d}' > /root/flag.txt && \
    chmod 600 /root/flag.txt

# ── Additional realism ──────────────────────────────────────────────
# Some red herrings for enumeration practice
RUN echo 'developer ALL=(ALL) NOPASSWD: /usr/local/bin/statuscheck' >> /etc/sudoers && \
    echo '#!/bin/bash\n# Nightly backup - runs as root via cron\ntar czf /tmp/backup.tar.gz /opt/meridian/projects/ 2>/dev/null' \
        > /opt/meridian/backup.sh && \
    chmod 755 /opt/meridian/backup.sh && \
    echo '0 2 * * * root /opt/meridian/backup.sh' > /etc/cron.d/meridian-backup

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
