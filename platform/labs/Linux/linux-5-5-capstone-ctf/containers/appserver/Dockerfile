FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd

# ── App user (pivot target) ──────────────────────────────────────────
RUN useradd -m -s /bin/bash appuser && \
    echo 'appuser:Z3n1th_App_2024#' | chpasswd

# ── SUID on python3 for privesc ──────────────────────────────────────
RUN chmod u+s /usr/bin/python3*

# ── Marker 2 (requires root) ────────────────────────────────────────
RUN printf 'pwn3d\n' > /root/marker.txt && chmod 600 /root/marker.txt

# ── Database credentials (found after privesc) ───────────────────────
RUN mkdir -p /opt/zenith && \
    printf 'DB_HOST=zenith-db\nDB_PORT=3306\nDB_NAME=zenith\nDB_USER=zenith_app\nDB_PASS=Z3n_DB_Pr0d#\n' > /opt/zenith/db.conf && \
    chmod 600 /opt/zenith/db.conf

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
