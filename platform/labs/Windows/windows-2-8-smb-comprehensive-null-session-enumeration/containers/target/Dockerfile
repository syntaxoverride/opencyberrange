FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Create users and groups for comprehensive enumeration
RUN useradd -M -s /bin/false admin && \
    useradd -M -s /bin/false user1 && \
    useradd -M -s /bin/false svc_backup && \
    echo "admin:password123" | chpasswd

# Configure Samba with null session, users, and shares
# Flag embedded in server string - visible during comprehensive enumeration
# NOTE: Do NOT manually define [IPC$] - Samba creates it automatically
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = FINANCECORP" >> /etc/samba/smb.conf && \
    echo "server string = WIN-DC01 - Full Enum: OCR{smb_c0mpl3t3_null}" >> /etc/samba/smb.conf && \
    echo "netbios name = WIN-DC01" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "guest account = nobody" >> /etc/samba/smb.conf && \
    echo "passdb backend = tdbsam" >> /etc/samba/smb.conf && \
    echo "null passwords = yes" >> /etc/samba/smb.conf && \
    echo "[public]" >> /etc/samba/smb.conf && \
    echo "comment = Public Share" >> /etc/samba/smb.conf && \
    echo "path = /tmp/public" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf && \
    echo "[data]" >> /etc/samba/smb.conf && \
    echo "comment = Data Share" >> /etc/samba/smb.conf && \
    echo "path = /tmp/data" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf

# Add users to Samba passdb so they're visible via enumdomusers
# Must start smbd first so passdb.tdb is properly initialized
RUN service smbd start && \
    printf 'password123\npassword123\n' | smbpasswd -a -s admin && \
    printf 'password123\npassword123\n' | smbpasswd -a -s user1 && \
    printf 'password123\npassword123\n' | smbpasswd -a -s svc_backup && \
    smbpasswd -e admin && smbpasswd -e user1 && smbpasswd -e svc_backup && \
    service smbd stop

# Create share directories
RUN mkdir -p /tmp/public /tmp/data

EXPOSE 445

CMD ["smbd", "-F", "--no-process-group"]
