FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*

# Create users for enumeration
RUN useradd -M -s /bin/false admin && \
    useradd -M -s /bin/false user1 && \
    useradd -M -s /bin/false guest && \
    echo "admin:password123" | chpasswd && \
    echo "user1:password123" | chpasswd

# Configure Samba with null session and users
# Flag embedded in server string - visible during user enumeration
# NOTE: Do NOT manually define [IPC$] - Samba creates it automatically
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = DC01 - Users Enumerable: OCR{smb_us3r_3num}" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "guest account = nobody" >> /etc/samba/smb.conf && \
    echo "passdb backend = tdbsam" >> /etc/samba/smb.conf && \
    echo "null passwords = yes" >> /etc/samba/smb.conf

# Add users to Samba passdb so they're visible via enumdomusers
# Must start smbd first so passdb.tdb is properly initialized
RUN service smbd start && \
    printf 'password123\npassword123\n' | smbpasswd -a -s admin && \
    printf 'password123\npassword123\n' | smbpasswd -a -s user1 && \
    printf '\n\n' | smbpasswd -a -s guest && \
    smbpasswd -e admin && smbpasswd -e user1 && smbpasswd -e guest && \
    service smbd stop

EXPOSE 445

CMD ["smbd", "-F", "--no-process-group"]
