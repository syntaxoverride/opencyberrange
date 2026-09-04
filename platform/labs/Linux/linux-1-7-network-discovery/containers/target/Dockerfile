FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    nginx \
    vsftpd \
    python3 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# ── SSH ──────────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── Web server (port 80). Token 1 (in HTML comment) ──────────────────
COPY index.html /var/www/html/index.html

# ── FTP server (port 21). Token 2 (anonymous access) ───────────────
RUN mkdir -p /srv/ftp/pub /var/run/vsftpd/empty && \
    printf '4n0n\n' > /srv/ftp/pub/token.txt && \
    cp /srv/ftp/pub/token.txt /srv/ftp/token.txt && \
    printf 'Orion TechWorks Public FTP\nContact: jake.morrison@orion-techworks.com\n' > /srv/ftp/welcome.txt

RUN printf 'listen=YES\n\
listen_ipv6=NO\n\
anonymous_enable=YES\n\
local_enable=NO\n\
write_enable=NO\n\
anon_root=/srv/ftp\n\
no_anon_password=YES\n\
xferlog_enable=YES\n\
connect_from_port_20=YES\n\
pasv_enable=YES\n\
pasv_min_port=30000\n\
pasv_max_port=30100\n\
pasv_promiscuous=YES\n\
seccomp_sandbox=NO\n' > /etc/vsftpd.conf

# ── Custom service (port 8888). Token 3 ────────────────────────────
RUN printf '#!/usr/bin/env python3\n\
import socket, threading\n\
\n\
BANNER = """Orion TechWorks Internal Monitoring Service v3.7\n\
Status: Active | Uptime: 47d 12h 33m\n\
Auth Token: h1dd3n\n\
Connection closed.\n\
"""\n\
\n\
def handle(conn):\n\
    try:\n\
        conn.sendall(BANNER.encode())\n\
    finally:\n\
        conn.close()\n\
\n\
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n\
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n\
s.bind(("0.0.0.0", 8888))\n\
s.listen(5)\n\
while True:\n\
    conn, addr = s.accept()\n\
    threading.Thread(target=handle, args=(conn,), daemon=True).start()\n' > /usr/local/bin/monitor-service.py && \
    chmod +x /usr/local/bin/monitor-service.py

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 21 22 80 8888

CMD ["/start.sh"]
