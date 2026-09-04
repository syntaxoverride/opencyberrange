FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    apache2 \
    ssl-cert \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# -- Enable SSL module and default SSL site ---------------------------------
RUN a2enmod ssl && a2ensite default-ssl

# -- Company intranet page --------------------------------------------------
COPY index.html /var/www/html/index.html

# -- Listeners on suspicious ports (so nmap shows them as open) -------------
# These simulate services that should NOT be reachable through the firewall
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80 443 22 3306 4444 8080

CMD ["/start.sh"]
