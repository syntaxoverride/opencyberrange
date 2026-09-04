FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    openssh-server \
    nginx \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd

# Create users
RUN useradd -m -s /bin/bash contractor && \
    echo "contractor:T1t4n_C0ntr4ct#" | chpasswd && \
    useradd -m -s /bin/bash sysadmin && \
    echo "sysadmin:T1t4n_Sys_2024#" | chpasswd

# Contractor's project notes with sysadmin credentials
RUN echo "=== Titan Global. Project Notes ===" > /home/contractor/project_notes.txt && \
    echo "" >> /home/contractor/project_notes.txt && \
    echo "Deployment Phase 2. Internal Systems" >> /home/contractor/project_notes.txt && \
    echo "Contact: J. Morrison (sysadmin team)" >> /home/contractor/project_notes.txt && \
    echo "" >> /home/contractor/project_notes.txt && \
    echo "Temp credentials for system migration:" >> /home/contractor/project_notes.txt && \
    echo "  User: sysadmin" >> /home/contractor/project_notes.txt && \
    echo "  Pass: T1t4n_Sys_2024#" >> /home/contractor/project_notes.txt && \
    echo "" >> /home/contractor/project_notes.txt && \
    echo "TODO: Remove these creds after migration complete" >> /home/contractor/project_notes.txt && \
    chown contractor:contractor /home/contractor/project_notes.txt

# Sysadmin's marker (token 2)
RUN echo "bl4ck" > /home/sysadmin/marker.txt && \
    chown sysadmin:sysadmin /home/sysadmin/marker.txt

# Sysadmin's SSH config with charlie credentials
RUN mkdir -p /home/sysadmin/.ssh && \
    echo "# Titan Infrastructure SSH Configs" > /home/sysadmin/.ssh/config && \
    echo "" >> /home/sysadmin/.ssh/config && \
    echo "Host charlie" >> /home/sysadmin/.ssh/config && \
    echo "    HostName server-charlie" >> /home/sysadmin/.ssh/config && \
    echo "    User operator" >> /home/sysadmin/.ssh/config && \
    echo "    # Password: T1t4n_0ps_2024#" >> /home/sysadmin/.ssh/config && \
    echo "    # Monitoring account. do not disable" >> /home/sysadmin/.ssh/config && \
    chown -R sysadmin:sysadmin /home/sysadmin/.ssh && \
    chmod 700 /home/sysadmin/.ssh && \
    chmod 600 /home/sysadmin/.ssh/config

# Web content
COPY index.html /var/www/html/index.html

# Nginx config. replace default
RUN echo 'server { \n\
    listen 80 default_server; \n\
    listen [::]:80 default_server; \n\
    root /var/www/html; \n\
    index index.html; \n\
    server_name _; \n\
    location / { \n\
        try_files $uri $uri/ =404; \n\
    } \n\
}' > /etc/nginx/sites-available/default

# SSH config
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22 80

CMD ["/start.sh"]
