FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Configure Samba with flag in server string (visible during connection test)
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = Windows Server - OCR{smb_c0nn3ct}" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "[public]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/public" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf && \
    echo "read only = yes" >> /etc/samba/smb.conf

# Create share directory
RUN mkdir -p /tmp/public

EXPOSE 445

CMD ["smbd", "-F", "--no-process-group"]
