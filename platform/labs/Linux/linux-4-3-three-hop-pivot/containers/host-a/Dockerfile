FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openssh-client \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd && \
    useradd -m -s /bin/bash teller && \
    echo 'teller:M3r1d14n_T3ll3r#' | chpasswd

# ── Banking application config (simulated) ───────────────────────────
RUN mkdir -p /var/www/banking-app/public \
             /var/www/banking-app/logs

# .env file contains leaked database credentials for host-b
RUN printf 'APP_NAME=Meridian Trust Online Banking\n\
APP_ENV=production\n\
APP_KEY=base64:mTb7xQ9rK2pL4wN8vF1yC6hA3jD5sG0oU\n\
APP_DEBUG=false\n\
APP_URL=https://banking.meridiantrust.com\n\
\n\
DB_CONNECTION=mysql\n\
DB_HOST=meridian-appsvr\n\
DB_PORT=3306\n\
DB_DATABASE=meridian_prod\n\
DB_USER=appuser\n\
DB_PASS=M3r1d14n_App_2024#\n\
\n\
REDIS_HOST=127.0.0.1\n\
REDIS_PORT=6379\n\
\n\
MAIL_MAILER=smtp\n\
MAIL_HOST=mail.meridiantrust.com\n\
MAIL_PORT=587\n\
\n\
SESSION_DRIVER=redis\n\
SESSION_LIFETIME=120\n' > /var/www/banking-app/.env

# ── Assessment token 1 ──────────────────────────────────────────────
RUN echo 'thr33' > /home/teller/assessment_token.txt && \
    chown teller:teller /home/teller/assessment_token.txt

# Set permissions. teller can read app files
RUN chown -R teller:teller /var/www/banking-app

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
