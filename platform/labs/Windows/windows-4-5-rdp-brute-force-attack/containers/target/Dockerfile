FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y xrdp xfce4 xfce4-terminal mousepad openssh-server && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/run/sshd
RUN useradd -m -s /bin/bash admin && echo "admin:qwerty" | chpasswd
RUN echo "OCR{rdp_brut3_f0rc3}" > /home/admin/flag.txt
EXPOSE 3389 22
CMD service ssh start && service xrdp start && tail -f /dev/null
