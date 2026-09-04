FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# ── SSH (accepts no valid logins) ────────────────────────────────────
RUN mkdir -p /run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo 'MaxAuthTries 2' >> /etc/ssh/sshd_config

# ── nginx. generic "Under Construction" page ────────────────────────
RUN printf '<!DOCTYPE html>\n\
<html lang="en">\n\
<head>\n\
    <meta charset="UTF-8">\n\
    <title>Site Under Construction</title>\n\
    <style>\n\
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee;\n\
               display: flex; align-items: center; justify-content: center;\n\
               height: 100vh; margin: 0; }\n\
        .box { text-align: center; padding: 40px; border: 1px solid #333;\n\
               border-radius: 8px; background: #16213e; }\n\
        h1 { color: #e94560; }\n\
    </style>\n\
</head>\n\
<body>\n\
    <div class="box">\n\
        <h1>Under Construction</h1>\n\
        <p>This site is currently being set up. Please check back later.</p>\n\
    </div>\n\
</body>\n\
</html>\n' > /var/www/html/index.html

EXPOSE 22 80

CMD service ssh start && nginx -g 'daemon off;'
