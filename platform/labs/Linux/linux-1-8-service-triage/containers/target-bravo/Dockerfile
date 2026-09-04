FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    apache2 \
    vsftpd \
    && rm -rf /var/lib/apt/lists/*

# ── Apache. 403 Forbidden page ─────────────────────────────────────
RUN printf '<!DOCTYPE html>\n\
<html lang="en">\n\
<head><meta charset="UTF-8"><title>403 Forbidden</title></head>\n\
<body>\n\
<h1>Forbidden</h1>\n\
<p>You do not have permission to access this resource.</p>\n\
<hr>\n\
<address>Apache/2.4.52 (Ubuntu) Server</address>\n\
</body>\n\
</html>\n' > /var/www/html/index.html && \
    printf '<Directory /var/www/html>\n\
    Options -Indexes\n\
    Require all denied\n\
</Directory>\n' > /etc/apache2/conf-available/deny-all.conf && \
    a2enconf deny-all

# ── FTP. anonymous access to an empty directory ─────────────────────
RUN mkdir -p /srv/ftp /var/run/vsftpd/empty && \
    printf 'listen=YES\n\
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

EXPOSE 21 80

CMD apachectl start && vsftpd /etc/vsftpd.conf
