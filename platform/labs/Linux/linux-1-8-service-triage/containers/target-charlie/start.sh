#!/bin/bash
nginx
vsftpd /etc/vsftpd.conf &
python3 /usr/local/bin/dispatch-service.py &
exec sleep infinity
