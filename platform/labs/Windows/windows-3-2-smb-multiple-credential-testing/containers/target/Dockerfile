FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*
# Create Linux user
RUN useradd -M -s /bin/false admin && echo "admin:admin123" | chpasswd

# Configure Samba
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "[private]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/private" >> /etc/samba/smb.conf && \
    echo "valid users = admin" >> /etc/samba/smb.conf && \
    echo "read only = no" >> /etc/samba/smb.conf

# Create share directory and flag
RUN mkdir -p /tmp/private && \
    echo "OCR{smb_mult1_4uth}" > /tmp/private/flag.txt

# Add user to Samba password database (required for SMB authentication)
RUN (echo "admin123"; echo "admin123") | smbpasswd -a -s admin
EXPOSE 445
CMD ["smbd", "-F", "--no-process-group"]