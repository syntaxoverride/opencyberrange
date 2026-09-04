#!/bin/bash
/usr/sbin/sshd
nginx
vsftpd /etc/vsftpd.conf &
python3 /usr/local/bin/monitor-service.py &
exec sleep infinity
