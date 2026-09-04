FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    vsftpd samba openssh-server \
    && rm -rf /var/lib/apt/lists/*

# --- vsftpd: anonymous access ---
RUN mkdir -p /srv/ftp /var/run/vsftpd/empty && \
    echo "anonymous_enable=YES" > /etc/vsftpd.conf && \
    echo "no_anon_password=YES" >> /etc/vsftpd.conf && \
    echo "write_enable=NO" >> /etc/vsftpd.conf && \
    echo "local_enable=NO" >> /etc/vsftpd.conf && \
    echo "anon_root=/srv/ftp" >> /etc/vsftpd.conf && \
    echo "listen=YES" >> /etc/vsftpd.conf && \
    echo "listen_ipv6=NO" >> /etc/vsftpd.conf && \
    echo "pasv_enable=YES" >> /etc/vsftpd.conf && \
    echo "pasv_min_port=30000" >> /etc/vsftpd.conf && \
    echo "pasv_max_port=30100" >> /etc/vsftpd.conf && \
    echo "pasv_promiscuous=YES" >> /etc/vsftpd.conf && \
    echo "seccomp_sandbox=NO" >> /etc/vsftpd.conf && \
    chown nobody:nogroup /srv/ftp

RUN echo "The domain controller on this subnet runs LDAP, RDP, SMB, and related services. The SMB server string contains critical deployment info for enumeration." > /srv/ftp/dc-audit-notes.txt && \
    echo "Flag Part 2 of 3: n3tw0rk" > /srv/ftp/welcome-packet.txt && \
    chown nobody:nogroup /srv/ftp/dc-audit-notes.txt /srv/ftp/welcome-packet.txt

# --- Samba: guest share ---
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = File Server" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "[public]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/public" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf

RUN mkdir -p /tmp/public && \
    echo "host,role,services" > /tmp/public/it-inventory.csv && \
    echo "webportal,Web Portal,HTTP" >> /tmp/public/it-inventory.csv && \
    echo "fileserver,File Server,FTP,SMB,SSH" >> /tmp/public/it-inventory.csv && \
    echo "dc,Domain Controller,LDAP,RDP,SMB" >> /tmp/public/it-inventory.csv && \
    echo "Flag Part 2 of 3: n3tw0rk" > /tmp/public/welcome-packet.txt && \
    chmod 755 /tmp/public && chmod 644 /tmp/public/*

# --- SSH on port 2222 ---
RUN useradd -m -s /bin/bash admin 2>/dev/null || true && echo "admin:admin" | chpasswd
RUN mkdir -p /var/run/sshd && \
    echo "Port 2222" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Breadcrumb: email fragment in admin's home directory rewards SSH discovery
RUN printf 'From: j.martinez@financecorp.com\nTo: admin@financecorp.com\nDate: Mon, 09 Dec 2024 14:23:00 -0500\nSubject: RE: FTP Server Migration\n\nHey,\n\nJust a heads up - the anonymous FTP access on this file server is still\nenabled. The audit files and deployment notes are sitting right in the\nFTP root. Can you make sure those get moved before the external pen test\nnext week?\n\nAlso, the DC team mentioned the SMB server string on the domain\ncontroller still has debug info baked in from the initial deployment.\nThey said they would fix it after the migration but I doubt they have.\nMight be worth flagging.\n\n- J\n' > /home/admin/migration_email.txt && \
    chown admin:admin /home/admin/migration_email.txt

EXPOSE 21 445 2222

CMD vsftpd /etc/vsftpd.conf & smbd -F --no-process-group & /usr/sbin/sshd -D
