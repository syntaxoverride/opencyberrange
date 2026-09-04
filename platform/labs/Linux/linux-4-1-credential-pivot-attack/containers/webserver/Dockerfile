FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openssh-client \
    nginx \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd && \
    useradd -m -s /bin/bash webdev && \
    echo 'webdev:Cr3st_W3b_2024#' | chpasswd

# ── Crestline Financial web application (simulated) ─────────────────
RUN mkdir -p /var/www/crestline-portal/config \
             /var/www/crestline-portal/public \
             /var/www/crestline-portal/logs

# Application .env file. contains leaked database credentials
RUN printf 'APP_NAME=Crestline Customer Portal\n\
APP_ENV=production\n\
APP_KEY=base64:kR3N9xLm2bP8vQ7wT5yA1jF6uH0iD4oS\n\
APP_DEBUG=false\n\
APP_URL=https://portal.crestline-financial.com\n\
\n\
DB_CONNECTION=pgsql\n\
DB_HOST=crestline-db\n\
DB_PORT=5432\n\
DB_DATABASE=crestline_prod\n\
DB_USER=dbadmin\n\
DB_PASS=F1n4nc3_DB_Pr0d#\n\
\n\
REDIS_HOST=127.0.0.1\n\
REDIS_PORT=6379\n\
\n\
MAIL_MAILER=smtp\n\
MAIL_HOST=mail.crestline-financial.com\n\
MAIL_PORT=587\n\
\n\
SESSION_DRIVER=redis\n\
SESSION_LIFETIME=120\n' > /var/www/crestline-portal/.env

# Config directory with backup files containing flag part 1
RUN printf '# Crestline Financial. API Key Configuration\n\
# Generated: 2024-07-15\n\
# Contact: nathan.cole@crestline-financial.com\n\
\n\
stripe_key=sk_live_4eC39HqLyjWDarjtT1zdp7dc\n\
plaid_key=pk_live_2bP8vQ7wT5yA1jF6uH0iD4oS\n\
assessment_token=cr3d\n\
internal_api_key=cfl_prod_a8f2e1b9c4d7\n' > /var/www/crestline-portal/config/api_keys.bak

RUN printf '# Database connection pool settings\n\
max_connections=25\n\
idle_timeout=300\n\
connection_string=postgresql://dbadmin:F1n4nc3_DB_Pr0d#@crestline-db:5432/crestline_prod\n' \
    > /var/www/crestline-portal/config/database.yml

# Corporate web content
COPY index.html /var/www/crestline-portal/public/index.html

# nginx config pointing to static site
RUN printf 'server {\n\
    listen 80;\n\
    root /var/www/crestline-portal/public;\n\
    index index.html;\n\
    location / { try_files $uri $uri/ =404; }\n\
}\n' > /etc/nginx/sites-available/default

# Set permissions. webdev can read app files (realistic for a service account)
RUN chown -R webdev:webdev /var/www/crestline-portal

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22 80

CMD ["/start.sh"]
