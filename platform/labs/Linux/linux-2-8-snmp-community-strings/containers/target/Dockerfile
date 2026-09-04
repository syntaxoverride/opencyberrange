FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    snmpd \
    snmp \
    && rm -rf /var/lib/apt/lists/*

# ── SNMP configuration with assessment tokens ───────────────────────
RUN printf '# Greystone Manufacturing. ICS Gateway SNMP Configuration\n\
\n\
# Community strings\n\
rocommunity public\n\
\n\
# System information. tokens embedded in standard MIB fields\n\
sysDescr    Greystone Manufacturing ICS Gateway v2.4.1 | Model: GS-7200 | Token: snmp\n\
sysLocation Factory Floor B, Rack 14, Pittsburgh PA | Asset: GW-0028 | Token: w4lk\n\
sysContact  OT Security Team (karl.weber@greystone-mfg.com) | Ext: 2847 | Token: c0mmun1ty\n\
sysName     greystone-gw01\n\
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

CMD ["/start.sh"]
