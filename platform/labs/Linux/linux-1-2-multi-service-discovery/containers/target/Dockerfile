FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install all required services
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    vsftpd \
    apache2 \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir -p /var/run/sshd && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

RUN useradd -m -s /bin/bash techstart && \
    echo "techstart:TechStart2024#" | chpasswd

# Configure vsftpd for anonymous access with flag part 1
RUN echo "listen=YES" > /etc/vsftpd.conf && \
    echo "listen_ipv6=NO" >> /etc/vsftpd.conf && \
    echo "anonymous_enable=YES" >> /etc/vsftpd.conf && \
    echo "local_enable=NO" >> /etc/vsftpd.conf && \
    echo "write_enable=NO" >> /etc/vsftpd.conf && \
    echo "anon_root=/srv/ftp" >> /etc/vsftpd.conf && \
    echo "no_anon_password=YES" >> /etc/vsftpd.conf && \
    echo "hide_ids=YES" >> /etc/vsftpd.conf && \
    echo "pasv_enable=YES" >> /etc/vsftpd.conf && \
    echo "pasv_min_port=40000" >> /etc/vsftpd.conf && \
    echo "pasv_max_port=40100" >> /etc/vsftpd.conf && \
    echo "pasv_promiscuous=YES" >> /etc/vsftpd.conf && \
    echo "seccomp_sandbox=NO" >> /etc/vsftpd.conf

# Create FTP directory with flag part 1
RUN mkdir -p /srv/ftp/pub && \
    echo "========================================" > /srv/ftp/pub/readme.txt && \
    echo "TechStart Inc. - File Transfer Server" >> /srv/ftp/pub/readme.txt && \
    echo "========================================" >> /srv/ftp/pub/readme.txt && \
    echo "" >> /srv/ftp/pub/readme.txt && \
    echo "Welcome to the TechStart FTP server." >> /srv/ftp/pub/readme.txt && \
    echo "For authorized file transfers only." >> /srv/ftp/pub/readme.txt && \
    echo "" >> /srv/ftp/pub/readme.txt && \
    echo "Flag Part 1: OCR{mult1_" >> /srv/ftp/pub/readme.txt && \
    echo "" >> /srv/ftp/pub/readme.txt && \
    echo "Contact: admin@techstart.local" >> /srv/ftp/pub/readme.txt && \
    chmod 644 /srv/ftp/pub/readme.txt

# Create vsftpd runtime directory
RUN mkdir -p /var/run/vsftpd/empty

# Configure Apache with flag part 2 in HTML
RUN echo '<!DOCTYPE html>' > /var/www/html/index.html && \
    echo '<html>' >> /var/www/html/index.html && \
    echo '<head><title>TechStart Web Server</title></head>' >> /var/www/html/index.html && \
    echo '<body>' >> /var/www/html/index.html && \
    echo '<h1>Welcome to TechStart</h1>' >> /var/www/html/index.html && \
    echo '<p>This is the internal web server for TechStart Inc.</p>' >> /var/www/html/index.html && \
    echo '<!-- Development notes: Flag Part 2: s3rv1c3} -->' >> /var/www/html/index.html && \
    echo '</body>' >> /var/www/html/index.html && \
    echo '</html>' >> /var/www/html/index.html

# Create flag file for reference
RUN echo "OCR{mult1_s3rv1c3}" > /root/flag.txt

# Create startup script
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'service vsftpd start' >> /start.sh && \
    echo 'service ssh start' >> /start.sh && \
    echo 'apache2ctl -D FOREGROUND' >> /start.sh && \
    chmod +x /start.sh

EXPOSE 21 22 80 40000-40100

CMD ["/start.sh"]
