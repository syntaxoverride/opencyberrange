FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    vsftpd samba openssh-server \
    && rm -rf /var/lib/apt/lists/*

# --- vsftpd: anonymous access on non-standard port 2121 ---
RUN mkdir -p /srv/ftp/archived-cases /var/run/vsftpd/empty && \
    printf 'listen=YES\n\
listen_ipv6=NO\n\
listen_port=2121\n\
anonymous_enable=YES\n\
no_anon_password=YES\n\
write_enable=NO\n\
local_enable=NO\n\
anon_root=/srv/ftp\n\
pasv_enable=YES\n\
pasv_min_port=40000\n\
pasv_max_port=40100\n\
pasv_promiscuous=YES\n\
seccomp_sandbox=NO\n' > /etc/vsftpd.conf && \
    chown nobody:nogroup /srv/ftp

RUN echo "This directory contains archived case files from 2025 and earlier." > /srv/ftp/readme.txt && \
    echo "Archived case files are stored in subdirectories by category." > /srv/ftp/archived-cases/index.txt && \
    printf 'Flag 2: d1sc0v3ry\n\nCase Management Server Access:\nThe case management server has a shared directory for archived records.\nTo connect, use:\n  smbclient //<case_mgmt_server_ip>/records -U attorney%%CaseFile2024#\n' > /srv/ftp/archived-cases/flag-part.txt && \
    chown -R nobody:nogroup /srv/ftp

# --- Samba: authenticated share (paralegal / Summer2024#) ---
RUN printf '[global]\n\
workgroup = PINNACLE\n\
server string = Pinnacle Legal Document Server\n\
security = user\n\
map to guest = Bad User\n\
log level = 0\n\
log file = /dev/null\n\
\n\
[cases]\n\
path = /srv/shares/cases\n\
valid users = paralegal\n\
read only = yes\n\
browsable = yes\n\
comment = Case Files\n' > /etc/samba/smb.conf

RUN useradd -m -s /bin/bash paralegal && \
    echo 'paralegal:Summer2024#' | chpasswd && \
    (echo 'Summer2024#'; echo 'Summer2024#') | smbpasswd -a -s paralegal

RUN mkdir -p /srv/shares/cases && \
    printf 'From: IT Department <it-support@pinnacle.legal>\nTo: All Staff\nDate: February 20, 2026\nSubject: Archived Case Files Migration\n\nAs part of our infrastructure consolidation, archived case files from\n2025 and earlier have been moved to a legacy FTP service for long-term\nstorage. This service runs on a non-standard port (2121) and allows\nanonymous read-only access for retrieval purposes.\n\nFiles are organized under the archived-cases directory.\n\nFor case records on the case management server, use the credentials\nprovided in the archived case files.\n\n- Pinnacle IT Team\n' > /srv/shares/cases/case-transfer-memo.txt && \
    printf 'client_id,client_name,status,assigned_attorney\n1001,Meridian Corp,Active,m.thompson\n1002,TechStart LLC,Active,d.chen\n1003,Greenfield Energy,Pending Review,j.ramirez\n1004,Atlas Manufacturing,Closed,k.patel\n1005,Summit Realty Group,Active,r.kessler\n' > /srv/shares/cases/client-contacts.csv && \
    chmod 755 /srv/shares/cases && chmod 644 /srv/shares/cases/*

# --- SSH on standard port 22 ---
RUN mkdir -p /var/run/sshd && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Breadcrumb: note in paralegal's home directory rewards SSH discovery
RUN printf 'PINNACLE LEGAL GROUP - IT NOTICE\n================================\n\nTo: Document Server Users\nFrom: Sarah Robinson, IT Administrator\nDate: February 22, 2026\n\nReminder: Archived case files from 2025 have been moved off this server\nto the legacy FTP archive service. The FTP service is running on port\n2121 with anonymous read-only access enabled.\n\nIf you need to retrieve archived files, connect to the FTP service on\nthis host using port 2121. No credentials are required.\n\nThe archived files also contain credentials for the case management\nserver if you need access to case records.\n\n- Sarah\n' > /home/paralegal/archive-notice.txt && \
    chown paralegal:paralegal /home/paralegal/archive-notice.txt

EXPOSE 22 445 2121

CMD vsftpd /etc/vsftpd.conf & smbd -F --no-process-group & /usr/sbin/sshd -D
