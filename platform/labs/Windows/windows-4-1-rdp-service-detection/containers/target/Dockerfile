FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y xrdp openssh-server && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/run/sshd
RUN useradd -m -s /bin/bash rdpuser && echo "rdpuser:password123" | chpasswd
RUN echo "OCR{rdp_d3t3ct}" > /home/rdpuser/flag.txt
EXPOSE 3389 22
CMD service ssh start && service xrdp start && tail -f /dev/null
