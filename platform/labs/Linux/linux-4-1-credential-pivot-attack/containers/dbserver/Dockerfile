FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd && \
    useradd -m -s /bin/bash dbadmin && \
    echo 'dbadmin:F1n4nc3_DB_Pr0d#' | chpasswd

# ── Realistic database server environment ────────────────────────────
RUN mkdir -p /home/dbadmin/maintenance \
             /home/dbadmin/backups \
             /var/lib/postgresql/data

# Maintenance scripts (flavor text)
RUN printf '#!/bin/bash\n# Nightly backup script\n# Runs via cron at 02:00 UTC\n\
pg_dump crestline_prod | gzip > /home/dbadmin/backups/crestline_$(date +%%Y%%m%%d).sql.gz\n\
find /home/dbadmin/backups/ -mtime +30 -delete\n' > /home/dbadmin/maintenance/nightly_backup.sh && \
    chmod +x /home/dbadmin/maintenance/nightly_backup.sh

RUN printf 'Crestline Financial. Database Server Status\n\
Last maintenance window: 2024-09-01\n\
PostgreSQL: 15.4\n\
Backup schedule: nightly at 02:00 UTC\n\
Disk usage: 42%% of 500GB\n\
Contact: nathan.cole@crestline-financial.com\n' > /home/dbadmin/maintenance/server_status.txt

# Flag part 2. assessment marker on the database server
RUN printf 'p1v0t\n' > /home/dbadmin/maintenance/assessment_token.txt

# Set ownership
RUN chown -R dbadmin:dbadmin /home/dbadmin

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
