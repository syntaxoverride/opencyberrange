FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    openssh-server \
    findutils \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd

# Create operator user
RUN useradd -m -s /bin/bash -g operator operator && \
    echo "operator:T1t4n_0ps_2024#" | chpasswd

# Operator readme
RUN echo "Standard operator account for Titan infrastructure monitoring" > /home/operator/readme.txt && \
    chown operator:operator /home/operator/readme.txt

# Root flag (token 3)
RUN echo "b0x" > /root/flag.txt && \
    chmod 600 /root/flag.txt

# Credentials for server-delta (accessible after privesc)
RUN mkdir -p /opt/titan && \
    echo "=== Titan Global. Service Credentials ===" > /opt/titan/credentials.txt && \
    echo "" >> /opt/titan/credentials.txt && \
    echo "Delta Workstation (Forensics Analyst):" >> /opt/titan/credentials.txt && \
    echo "  Host: server-delta" >> /opt/titan/credentials.txt && \
    echo "  User: analyst" >> /opt/titan/credentials.txt && \
    echo "  Pass: T1t4n_4n4lyst#" >> /opt/titan/credentials.txt && \
    echo "" >> /opt/titan/credentials.txt && \
    echo "Note: Evidence analysis workstation. restricted access" >> /opt/titan/credentials.txt && \
    chmod 600 /opt/titan/credentials.txt

# Set SUID on find
RUN chmod u+s /usr/bin/find

# SSH config
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

EXPOSE 22

CMD ["/bin/bash", "-c", "ssh-keygen -A && /usr/sbin/sshd -D"]
