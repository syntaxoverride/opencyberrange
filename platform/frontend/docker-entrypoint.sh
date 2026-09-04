#!/bin/sh
# Auto-detect TLS certificates and swap nginx config accordingly.
# If /etc/nginx/certs/selfsigned.crt exists, use the SSL config.
# Otherwise, serve HTTP-only (Cloudflare Tunnel or dev mode).

if [ -f /etc/nginx/certs/selfsigned.crt ] && [ -f /etc/nginx/certs/selfsigned.key ]; then
    echo "[entrypoint] TLS certificates found — enabling HTTPS on port 443"
    cp /etc/nginx/conf.d/nginx-ssl.conf /etc/nginx/conf.d/default.conf
    rm -f /etc/nginx/conf.d/nginx-ssl.conf
else
    echo "[entrypoint] No TLS certificates — serving HTTP only on port 80"
    rm -f /etc/nginx/conf.d/nginx-ssl.conf
fi

exec nginx -g 'daemon off;'
