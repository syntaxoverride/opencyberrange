FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y openssh-server && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash admin && echo "admin:qwerty" | chpasswd
RUN echo "OCR{w1nrm_brut3}" > /home/admin/flag.txt
RUN mkdir /var/run/sshd
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]