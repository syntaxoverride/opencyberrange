FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    vsftpd \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# ── Web server (port 80). Token 1 in HTML comment ──────────────────
COPY index.html /var/www/html/index.html

# ── FTP server (port 21). Token 2 via anonymous access ─────────────
RUN mkdir -p /srv/ftp /var/run/vsftpd/empty && \
    printf 'r34l\n' > /srv/ftp/token.txt && \
    printf 'Vanguard Logistics Secure FTP\nContact: dana.reeves@vanguard-logistics.com\n' > /srv/ftp/readme.txt

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

# ── Custom service (port 9999). Token 3 in banner ──────────────────
RUN printf '#!/usr/bin/env python3\n\
import socket, threading\n\
\n\
BANNER = """Vanguard Logistics Dispatch Relay v2.4\\n\
Status: Online | Uptime: 83d 06h 17m\\n\
Auth Token: t4rg3t\\n\
Connection closed.\\n\
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
s.bind(("0.0.0.0", 9999))\n\
s.listen(5)\n\
while True:\n\
    conn, addr = s.accept()\n\
    threading.Thread(target=handle, args=(conn,), daemon=True).start()\n' > /usr/local/bin/dispatch-service.py && \
    chmod +x /usr/local/bin/dispatch-service.py

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 21 80 9999

CMD ["/start.sh"]
