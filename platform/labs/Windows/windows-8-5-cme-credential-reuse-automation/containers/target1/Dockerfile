FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install Samba for SMB service
RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Create user with credentials
RUN useradd -M -s /bin/false admin && echo "admin:password123" | chpasswd

# Configure Samba
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "[private]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/private" >> /etc/samba/smb.conf && \
    echo "valid users = admin" >> /etc/samba/smb.conf && \
    echo "read only = no" >> /etc/samba/smb.conf
RUN printf 'password123\npassword123\n' | smbpasswd -a -s admin

# Create share directory and flag
RUN mkdir -p /tmp/private && \
    echo "OCR{cme_smb_cr3d3nt14l_t3st}" > /tmp/private/flag.txt && \
    chown -R admin:admin /tmp/private

EXPOSE 445
CMD ["smbd", "-F", "--no-process-group"]

