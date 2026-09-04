#!/bin/bash

# Start dummy listeners on suspicious ports so traffic-gen connections
# register as established (not refused). These simulate vulnerable services.
while true; do nc -l -p 22 -q 0 < /dev/null 2>/dev/null; done &
while true; do nc -l -p 3306 -q 0 < /dev/null 2>/dev/null; done &
while true; do nc -l -p 4444 -q 0 < /dev/null 2>/dev/null; done &
while true; do nc -l -p 8080 -q 0 < /dev/null 2>/dev/null; done &

# Start Apache in foreground (serves HTTP on 80 and HTTPS on 443)
exec apache2ctl -D FOREGROUND
