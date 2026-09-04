FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    findutils \
    && rm -rf /var/lib/apt/lists/*

# ── SSH configuration ────────────────────────────────────────────────
RUN mkdir -p /run/sshd
RUN sed -i 's/#PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# ── Create service account ──────────────────────────────────────────
RUN useradd -m -s /bin/bash svcproc && \
    echo 'svcproc:Pr0c_SSH_2025#' | chpasswd

# ── Place assessment markers ────────────────────────────────────────
# Token 3 (p1v0t). readable by svcproc user
RUN echo "p1v0t" > /home/svcproc/marker.txt && \
    chown svcproc:svcproc /home/svcproc/marker.txt && \
    chmod 644 /home/svcproc/marker.txt

# Token 4 (r00t3d). requires root access
RUN echo "r00t3d" > /root/flag.txt && \
    chmod 600 /root/flag.txt

# ── SUID binary for privilege escalation ────────────────────────────
# Set SUID bit on find. exploitable via: find . -exec /bin/sh -p \; -quit
RUN chmod u+s /usr/bin/find

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
