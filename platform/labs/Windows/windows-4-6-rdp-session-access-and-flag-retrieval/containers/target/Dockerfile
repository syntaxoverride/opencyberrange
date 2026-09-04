FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y xrdp xfce4 xfce4-terminal mousepad openssh-server && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/run/sshd
RUN useradd -m -s /bin/bash admin && echo "admin:password123" | chpasswd
RUN mkdir -p /home/admin/Desktop && echo "OCR{rdp_s3ss10n_4cc3ss}" > /home/admin/Desktop/flag.txt
EXPOSE 3389 22
CMD service ssh start && service xrdp start && tail -f /dev/null
