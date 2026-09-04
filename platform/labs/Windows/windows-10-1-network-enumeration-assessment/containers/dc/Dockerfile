FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    samba \
    xrdp \
    slapd \
    ldap-utils \
    socat \
    && rm -rf /var/lib/apt/lists/*

# Configure Samba - Flag Part 3 embedded in server string for enumeration discovery
# Students find flag by running: smbclient -L //<ip> -N
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = FINANCECORP" >> /etc/samba/smb.conf && \
    echo "server string = Windows Server 2019 DC - Flag Part 3 of 3: 3num" >> /etc/samba/smb.conf && \
    echo "netbios name = WIN-DC01" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = Bad User" >> /etc/samba/smb.conf && \
    echo "log level = 0" >> /etc/samba/smb.conf && \
    echo "log file = /dev/null" >> /etc/samba/smb.conf

EXPOSE 88 139 389 445 3389

# Port 88 (Kerberos): socat listener so port appears open for enumeration; real KDC not required
CMD socat TCP-LISTEN:88,fork,reuseaddr EXEC:/bin/true & service smbd start && service xrdp start && /usr/sbin/slapd -h "ldap:///" -g openldap -u openldap -d 0