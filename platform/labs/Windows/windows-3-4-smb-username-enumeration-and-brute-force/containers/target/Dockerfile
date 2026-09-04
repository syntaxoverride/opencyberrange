FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install Samba
RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Create Linux user
RUN useradd -M -s /bin/false user1 && echo "user1:password123" | chpasswd

# Configure Samba
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = FinanceCorp SMB Server" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "[IPC$]" >> /etc/samba/smb.conf && \
    echo "path = /tmp" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf && \
    echo "[private]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/private" >> /etc/samba/smb.conf && \
    echo "valid users = user1" >> /etc/samba/smb.conf && \
    echo "read only = no" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf

# Create share directory and flag
RUN mkdir -p /tmp/private && \
    echo "OCR{smb_3num_brut3}" > /tmp/private/flag.txt

# Add user to Samba password database (required for SMB authentication)
RUN (echo "password123"; echo "password123") | smbpasswd -a -s user1

EXPOSE 445
CMD ["smbd", "-F", "--no-process-group"]