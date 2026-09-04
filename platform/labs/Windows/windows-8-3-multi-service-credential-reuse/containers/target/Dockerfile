FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y samba xrdp openssh-server && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash admin && echo "admin:password123" | chpasswd
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "[private]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/private" >> /etc/samba/smb.conf && \
    echo "valid users = admin" >> /etc/samba/smb.conf
RUN printf 'password123\npassword123\n' | smbpasswd -a -s admin
RUN mkdir -p /tmp/private && echo "OCR{cr3d_r3us3_mult1}" > /tmp/private/flag.txt
RUN mkdir /var/run/sshd
EXPOSE 445 3389 22
CMD service smbd start && service xrdp start && /usr/sbin/sshd -D