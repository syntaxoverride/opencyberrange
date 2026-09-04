#!/bin/bash
# Crestline Financial: Web Server startup

/usr/sbin/sshd
nginx

echo "[webserver] Crestline web server online"
exec sleep infinity
