FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y samba && rm -rf /var/lib/apt/lists/*
RUN useradd -M -s /bin/false admin && echo "admin:password123" | chpasswd
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "[share1]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/share1" >> /etc/samba/smb.conf && \
    echo "valid users = admin" >> /etc/samba/smb.conf && \
    echo "[share2]" >> /etc/samba/smb.conf && \
    echo "path = /tmp/share2" >> /etc/samba/smb.conf && \
    echo "valid users = admin" >> /etc/samba/smb.conf
RUN printf 'password123\npassword123\n' | smbpasswd -a -s admin
RUN mkdir -p /tmp/share1 /tmp/share2 && \
    echo "OCR{cr3d_r3us3_s4m3}" > /tmp/share2/flag.txt
EXPOSE 445
CMD ["smbd", "-F", "--no-process-group"]