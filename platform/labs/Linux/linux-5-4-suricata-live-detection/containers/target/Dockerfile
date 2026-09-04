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
    echo 'webadmin:Dmz_Adm1n_2024#' | chpasswd

# ── nginx configuration ─────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf

# ── Corporate web portal ────────────────────────────────────────────
RUN mkdir -p /var/www/html && \
    printf '<!DOCTYPE html>\n\
<html lang="en">\n\
<head>\n\
    <meta charset="UTF-8">\n\
    <title>Sentinel Defense Corp</title>\n\
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
        <h1>SENTINEL DEFENSE CORP</h1>\n\
        <p>Advanced Cybersecurity Solutions &bull; Threat Intelligence &bull; Incident Response</p>\n\
    </div>\n\
    <div class="content">\n\
        <div class="card">\n\
            <h2>About Us</h2>\n\
            <p>Sentinel Defense Corp is a premier cybersecurity consulting firm specializing in\n\
            penetration testing, threat hunting, and security operations center design. Founded\n\
            in 2018, we protect critical infrastructure across the defense, finance, and healthcare sectors.</p>\n\
        </div>\n\
        <div class="card">\n\
            <h2>Our Services</h2>\n\
            <ul class="services">\n\
                <li>Red Team Assessments &amp; Adversary Simulation</li>\n\
                <li>24/7 Managed Detection &amp; Response</li>\n\
                <li>ICS/SCADA Security Assessments</li>\n\
                <li>Cloud Security Architecture Review</li>\n\
                <li>Incident Response &amp; Digital Forensics</li>\n\
            </ul>\n\
        </div>\n\
        <div class="card">\n\
            <h2>Contact</h2>\n\
            <p>Email: contact@sentineldefense.corp<br>\n\
            Phone: (703) 555-0142<br>\n\
            Location: 1400 Wilson Blvd, Suite 800, Arlington, VA 22209</p>\n\
        </div>\n\
    </div>\n\
    <div class="footer">\n\
        &copy; 2024 Sentinel Defense Corp. All rights reserved. | CAGE Code: 9Z1X7 | DUNS: 08-472-1193\n\
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
