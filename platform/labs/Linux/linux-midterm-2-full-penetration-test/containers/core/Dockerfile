FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server findutils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd

# ── Deploy user (pivot target) ───────────────────────────────────────
RUN useradd -m -s /bin/bash deploy && \
    echo 'deploy:N3xus_D3pl0y#' | chpasswd

# Marker 2. accessible as deploy
RUN printf '3sc4l4t3\n' > /home/deploy/marker2.txt && \
    chown deploy:deploy /home/deploy/marker2.txt

# ── SUID misconfiguration for privesc ────────────────────────────────
RUN chmod u+s /usr/bin/find

# Marker 3. requires root (via SUID find)
RUN printf '0wn3d\n' > /root/marker3.txt && chmod 600 /root/marker3.txt

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
