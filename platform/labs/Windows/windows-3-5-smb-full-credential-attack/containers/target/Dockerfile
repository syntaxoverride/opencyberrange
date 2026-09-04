FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install Samba
RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Create Linux users
RUN useradd -M -s /bin/false admin && echo "admin:admin" | chpasswd && \
    useradd -M -s /bin/false user1 && echo "user1:password" | chpasswd && \
    useradd -M -s /bin/false test && echo "test:test123" | chpasswd

# Configure Samba
# NOTE: Do NOT manually define [IPC$] - Samba creates it automatically
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = FinanceCorp SMB Server" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "guest account = nobody" >> /etc/samba/smb.conf && \
    echo "[flag]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/flag" >> /etc/samba/smb.conf && \
    echo "valid users = admin,user1,test" >> /etc/samba/smb.conf && \
    echo "read only = no" >> /etc/samba/smb.conf && \
    echo "browseable = yes" >> /etc/samba/smb.conf

# Create share directory and flag
RUN mkdir -p /tmp/flag && \
    echo "OCR{smb_full_4tt4ck}" > /tmp/flag/flag.txt

# Add users to Samba password database (required for SMB authentication)
RUN (echo "admin"; echo "admin") | smbpasswd -a -s admin && \
    (echo "password"; echo "password") | smbpasswd -a -s user1 && \
    (echo "test123"; echo "test123") | smbpasswd -a -s test

EXPOSE 445
CMD ["smbd", "-F", "--no-process-group"]