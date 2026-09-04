FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Configure Samba with null session and multiple shares
# Flag embedded in share comment - visible during null session share enumeration
# NOTE: Do NOT manually define [IPC$] - Samba creates it automatically
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = Windows Server" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "guest account = nobody" >> /etc/samba/smb.conf && \
    echo "[public]" >> /etc/samba/smb.conf && \
    echo "comment = Public Share" >> /etc/samba/smb.conf && \
    echo "path = /tmp/public" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf && \
    echo "[admin_backup]" >> /etc/samba/smb.conf && \
    echo "comment = OCR{smb_null_3num}" >> /etc/samba/smb.conf && \
    echo "path = /tmp/backup" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf

# Create share directories
RUN mkdir -p /tmp/public /tmp/backup

EXPOSE 445

CMD ["smbd", "-F", "--no-process-group"]
