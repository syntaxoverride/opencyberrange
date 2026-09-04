FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iptables \
    iproute2 \
    tcpdump \
    net-tools \
    sudo \
    procps \
    && rm -rf /var/lib/apt/lists/*

# -- SSH setup -------------------------------------------------------------
RUN mkdir -p /run/sshd

# -- analyst user (student logs in here) ------------------------------------
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:M3r1d14n_Fw#' | chpasswd && \
    usermod -aG sudo analyst && \
    echo 'analyst ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/analyst

# -- Flag (only revealed by check-rules) ------------------------------------
RUN echo 'OCR{d3f4ult_d3ny_m4st3r}' > /root/flag.txt && \
    chmod 600 /root/flag.txt

# -- Monitor script ---------------------------------------------------------
COPY monitor /usr/local/bin/monitor
RUN chmod +x /usr/local/bin/monitor

# -- Rule checker script ----------------------------------------------------
COPY check-rules /usr/local/bin/check-rules
RUN chmod +x /usr/local/bin/check-rules

# -- Startup script ---------------------------------------------------------
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
