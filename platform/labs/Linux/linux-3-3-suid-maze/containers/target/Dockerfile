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
    iputils-ping \
    mount \
    && rm -rf /var/lib/apt/lists/*

# -- Analyst user (student SSH access) ----------------------------------------
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:C0b4lt_4n4lyst#' | chpasswd

# -- SSH setup ----------------------------------------------------------------
RUN mkdir -p /run/sshd

# -- Cobalt Systems environment ------------------------------------------------
RUN mkdir -p /opt/cobalt/logs && \
    echo 'Cobalt Systems. Monitoring Server (cobalt-mon01)\n\
Last patched: 2025-01-14\n\
Contact: marcus.webb@cobaltsystems.com\n\
Note: Ops tools installed per ticket OPS-4891' > /etc/motd

# -- SUID binaries setup ------------------------------------------------------
# 1. /usr/bin/ping  . standard system binary (already SUID on many systems)
RUN chmod u+s /usr/bin/ping

# 2. /usr/bin/su    . standard system binary (normally SUID)
RUN chmod u+s /usr/bin/su

# 3. /usr/bin/mount . standard system binary (normally SUID)
RUN chmod u+s /usr/bin/mount

# 4. /usr/local/bin/statusmon. custom decoy (prints system info, not exploitable)
RUN printf '#!/bin/bash\necho "=== Cobalt Systems Status Monitor v2.1 ==="\necho "Hostname: $(hostname)"\necho "Uptime:   $(uptime -p)"\necho "Disk:     $(df -h / | tail -1)"\necho "Memory:   $(free -h | grep Mem | awk '"'"'{print $3 "/" $2}'"'"')"\necho "Load:     $(cat /proc/loadavg | cut -d\" \" -f1-3)"\nexit 0\n' \
        > /usr/local/bin/statusmon && \
    chmod 4755 /usr/local/bin/statusmon

# 5. /usr/bin/find  . EXPLOITABLE (SUID misconfiguration)
RUN chmod u+s /usr/bin/find

# -- Cobalt readme listing SUID binaries (breadcrumb) -------------------------
RUN printf 'Cobalt Systems. Monitoring Server SUID Audit\n\
================================================================\n\
Date: 2025-01-14\n\
Auditor: Marcus Webb\n\n\
The following binaries have the SUID bit set on this server:\n\n\
  1. /usr/bin/ping      . Standard. Required for network diagnostics.\n\
  2. /usr/bin/su         . Standard. Required for user switching.\n\
  3. /usr/bin/mount      . Standard. Required for filesystem operations.\n\
  4. /usr/local/bin/statusmon. Custom. Ops team monitoring tool (OPS-4891).\n\
  5. /usr/bin/find       . Custom install. Ops team requested elevated\n\
                            permissions for scheduled file audits (OPS-5023).\n\n\
Assessment: All entries reviewed. No escalation risk identified.\n\
Next audit scheduled: 2025-07-14\n' > /opt/cobalt/readme.txt && \
    chmod 644 /opt/cobalt/readme.txt

# -- Clue file (token 1) ------------------------------------------------------
RUN printf 'Cobalt Systems. Analyst Briefing\n\
================================================================\n\
\n\
Welcome to the monitoring server. Your account has standard analyst\n\
permissions. The IT team installed several tools with elevated\n\
permissions on this system. Only one is dangerous.\n\
\n\
Token 1: su1d_m4z3\n\
\n\
Find the second token to complete your assessment. It requires\n\
elevated access. Look for misconfigurations among the SUID binaries.\n' > /home/analyst/clue.txt && \
    chown analyst:analyst /home/analyst/clue.txt && \
    chmod 644 /home/analyst/clue.txt

# -- Flag (token 2, root only) ------------------------------------------------
RUN echo 'p01s0n' > /root/flag.txt && \
    chmod 600 /root/flag.txt

# -- Additional realism -------------------------------------------------------
# Fake log files so statusmon looks legitimate
RUN echo '2025-01-15 08:00:01 statusmon: scheduled health check. OK' > /opt/cobalt/logs/monitor.log && \
    echo '2025-01-15 12:00:01 statusmon: scheduled health check. OK' >> /opt/cobalt/logs/monitor.log && \
    echo '2025-01-15 16:00:01 statusmon: scheduled health check. OK' >> /opt/cobalt/logs/monitor.log && \
    chmod 644 /opt/cobalt/logs/monitor.log

# Cron entry for realism
RUN echo '0 */4 * * * root /usr/local/bin/statusmon >> /opt/cobalt/logs/monitor.log 2>&1' > /etc/cron.d/cobalt-monitor && \
    chmod 644 /etc/cron.d/cobalt-monitor

# Bash history breadcrumb for analyst
RUN mkdir -p /home/analyst && \
    printf 'ls -la\ncat /opt/cobalt/readme.txt\nfind / -perm -4000 -type f 2>/dev/null\nstatusmon\n' > /home/analyst/.bash_history && \
    chown analyst:analyst /home/analyst/.bash_history

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
