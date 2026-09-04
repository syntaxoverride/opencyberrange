FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# ── SSH setup ────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd && \
    useradd -m -s /bin/bash -G adm webadmin && \
    echo 'webadmin:A3g1s_Adm1n#' | chpasswd

# ── nginx configuration ─────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf

# ── Corporate web portal ────────────────────────────────────────────
RUN mkdir -p /var/www/html && \
    printf '<!DOCTYPE html>\n\
<html lang="en">\n\
<head>\n\
    <meta charset="UTF-8">\n\
    <title>Aegis Security Corp</title>\n\
    <style>\n\
        body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; padding: 0; background: #0a0a1a; color: #e0e0e0; }\n\
        .header { background: linear-gradient(135deg, #1a1a3e 0%%, #0d2137 100%%); padding: 40px; text-align: center; border-bottom: 2px solid #00b4d8; }\n\
        .header h1 { color: #00b4d8; margin: 0; font-size: 2em; letter-spacing: 2px; }\n\
        .header p { color: #8899aa; margin-top: 10px; }\n\
        .content { max-width: 900px; margin: 40px auto; padding: 0 20px; }\n\
        .card { background: #111133; border: 1px solid #222255; border-radius: 8px; padding: 30px; margin: 20px 0; }\n\
        .card h2 { color: #00b4d8; margin-top: 0; }\n\
        .services li { margin: 8px 0; }\n\
        .footer { text-align: center; padding: 20px; color: #445566; font-size: 0.85em; border-top: 1px solid #222255; margin-top: 60px; }\n\
    </style>\n\
</head>\n\
<body>\n\
    <div class="header">\n\
        <h1>AEGIS SECURITY CORP</h1>\n\
        <p>Managed Security Services &bull; Threat Intelligence &bull; Incident Response</p>\n\
    </div>\n\
    <div class="content">\n\
        <div class="card">\n\
            <h2>About Us</h2>\n\
            <p>Aegis Security Corp is a leading managed security services provider specializing in\n\
            real-time threat detection, SOC operations, and advanced incident response. Founded\n\
            in 2019, we protect enterprises across the finance, healthcare, and technology sectors.</p>\n\
        </div>\n\
        <div class="card">\n\
            <h2>Our Services</h2>\n\
            <ul class="services">\n\
                <li>24/7 Security Operations Center (SOC)</li>\n\
                <li>Managed Detection &amp; Response (MDR)</li>\n\
                <li>Threat Intelligence &amp; Hunting</li>\n\
                <li>Cloud Security Posture Management</li>\n\
                <li>Incident Response &amp; Digital Forensics</li>\n\
            </ul>\n\
        </div>\n\
        <div class="card">\n\
            <h2>Contact</h2>\n\
            <p>Email: contact@aegissecurity.corp<br>\n\
            Phone: (303) 555-0198<br>\n\
            Location: 1801 California St, Suite 2400, Denver, CO 80202</p>\n\
        </div>\n\
    </div>\n\
    <div class="footer">\n\
        &copy; 2024 Aegis Security Corp. All rights reserved. | SOC 2 Type II Certified\n\
    </div>\n\
</body>\n\
</html>\n' > /var/www/html/index.html

# Error page for the attacker's probes
RUN printf '<!DOCTYPE html><html><body><h1>403 Forbidden</h1></body></html>\n' > /var/www/html/403.html

# Ensure nginx access log exists for the student to examine
RUN touch /var/log/nginx/access.log && \
    chown www-data:adm /var/log/nginx/access.log

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22 80

CMD ["/start.sh"]
