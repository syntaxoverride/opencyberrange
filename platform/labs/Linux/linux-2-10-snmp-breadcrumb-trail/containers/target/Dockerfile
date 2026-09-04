FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    snmpd \
    snmp \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# ── SSH configuration ─────────────────────────────────────────────
RUN mkdir -p /run/sshd && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'UseDNS no' >> /etc/ssh/sshd_config

# ── Create SSH user with credentials ─────────────────────────────
RUN useradd -m -s /bin/bash ops_user && \
    echo 'ops_user:R1dg3_0ps_2024#' | chpasswd

# ── Place flag in user home directory ─────────────────────────────
RUN echo 'OCR{snmp_ch41n_l0g1n}' > /home/ops_user/flag.txt && \
    chown ops_user:ops_user /home/ops_user/flag.txt && \
    chmod 400 /home/ops_user/flag.txt

# ── SNMP configuration with two community strings ────────────────
# "public" community. sysDescr leaks the internal community name
# "internal" community. sysContact leaks SSH credentials
RUN printf '# Ridgeline Power Systems. ICS Gateway SNMP Configuration\n\
\n\
# Community strings\n\
rocommunity public\n\
rocommunity internal\n\
\n\
# System information. public community breadcrumbs\n\
sysDescr    Ridgeline ICS Gateway v2.1 | internal-community: internal | Token: snmp_ch41n\n\
sysLocation Ridgeline Power Systems, Turbine Control Room 3, Montana | Asset: GW-0033\n\
sysContact  SSH Creds - ops_user / R1dg3_0ps_2024# | Token: l0g1n\n\
sysName     ridgeline-gw01\n\
\n\
# Listen on all interfaces\n\
agentAddress udp:161\n\
\n\
# Allow full MIB tree access\n\
view all included .1\n\
rouser noAuthUser\n' > /etc/snmp/snmpd.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 161/udp
EXPOSE 22

CMD ["/start.sh"]
