FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install ProFTPD
RUN apt-get update && apt-get install -y --no-install-recommends \
    proftpd-basic \
    && rm -rf /var/lib/apt/lists/*

# Create a comprehensive FTP welcome banner with the flag
RUN echo "======================================" > /etc/proftpd/welcome.txt && \
    echo "Welcome to the TechStart file transfer service" >> /etc/proftpd/welcome.txt && \
    echo "This server is for authorized use only" >> /etc/proftpd/welcome.txt && \
    echo "" >> /etc/proftpd/welcome.txt && \
    echo "Server: ProFTPD 1.3.5" >> /etc/proftpd/welcome.txt && \
    echo "Flag: OCR{ftp_1nt3r4ct}" >> /etc/proftpd/welcome.txt && \
    echo "" >> /etc/proftpd/welcome.txt && \
    echo "For support contact: it@techstart.local" >> /etc/proftpd/welcome.txt && \
    echo "======================================" >> /etc/proftpd/welcome.txt

# Configure ProFTPD with the custom banner
RUN echo "ServerName \"TechStart FTP Server\"" > /etc/proftpd/proftpd.conf && \
    echo "ServerType standalone" >> /etc/proftpd/proftpd.conf && \
    echo "DefaultServer on" >> /etc/proftpd/proftpd.conf && \
    echo "Port 21" >> /etc/proftpd/proftpd.conf && \
    echo "Umask 022" >> /etc/proftpd/proftpd.conf && \
    echo "MaxInstances 30" >> /etc/proftpd/proftpd.conf && \
    echo "User proftpd" >> /etc/proftpd/proftpd.conf && \
    echo "Group nogroup" >> /etc/proftpd/proftpd.conf && \
    echo "DisplayConnect /etc/proftpd/welcome.txt" >> /etc/proftpd/proftpd.conf && \
    echo "<Anonymous ~ftp>" >> /etc/proftpd/proftpd.conf && \
    echo "  User ftp" >> /etc/proftpd/proftpd.conf && \
    echo "  Group nogroup" >> /etc/proftpd/proftpd.conf && \
    echo "  UserAlias anonymous ftp" >> /etc/proftpd/proftpd.conf && \
    echo "  DirFakeUser on ftp" >> /etc/proftpd/proftpd.conf && \
    echo "  DirFakeGroup on ftp" >> /etc/proftpd/proftpd.conf && \
    echo "  RequireValidShell off" >> /etc/proftpd/proftpd.conf && \
    echo "  <Limit WRITE>" >> /etc/proftpd/proftpd.conf && \
    echo "    DenyAll" >> /etc/proftpd/proftpd.conf && \
    echo "  </Limit>" >> /etc/proftpd/proftpd.conf && \
    echo "</Anonymous>" >> /etc/proftpd/proftpd.conf

# Create flag file for reference
RUN echo "OCR{ftp_1nt3r4ct}" > /root/flag.txt

EXPOSE 21

CMD ["proftpd", "--nodaemon"]
