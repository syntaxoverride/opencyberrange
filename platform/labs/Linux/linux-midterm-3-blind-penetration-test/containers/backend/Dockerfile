FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server findutils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd

# -- Deploy user (pivot target) ----------------------------------------
RUN useradd -m -s /bin/bash deploy && \
    echo 'deploy:Ap3x_D3pl0y_2024#' | chpasswd

# Marker 2. accessible as deploy
RUN printf 'p1v0t\n' > /home/deploy/marker.txt && \
    chown deploy:deploy /home/deploy/marker.txt

# -- SUID misconfiguration for privesc ---------------------------------
RUN chmod u+s /usr/bin/find

# Marker 3. requires root (via SUID find)
RUN printf 'r00t3d\n' > /root/flag.txt && chmod 600 /root/flag.txt

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
