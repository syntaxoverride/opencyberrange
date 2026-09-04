FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y openssh-server python3 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash admin && echo "admin:password123" | chpasswd
RUN echo "OCR{w1nrm_3num}" > /home/admin/flag.txt
RUN mkdir /var/run/sshd

# WinRM simulation HTTP server (responds with Microsoft-HTTPAPI headers)
COPY winrm-simulator.py /usr/local/bin/winrm-simulator.py
RUN chmod +x /usr/local/bin/winrm-simulator.py

# Startup script runs SSH + WinRM simulators on ports 5985/5986
COPY start-services.sh /start-services.sh
RUN chmod +x /start-services.sh

EXPOSE 22 5985 5986
CMD ["/start-services.sh"]
