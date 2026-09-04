FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Create SSH directory and generate host keys
RUN mkdir -p /var/run/sshd && ssh-keygen -A

# Create user account (discoverable via NSE enumeration)
RUN useradd -m -s /bin/bash student && echo "student:techstart2024" | chpasswd

# Configure SSH banner containing the flag (visible during SSH authentication)
RUN printf 'TechStart SSH Server - Secure Access Only\nEnumeration flag: OCR{nse_scr1pt}\n' > /etc/ssh/banner.txt

# Configure sshd to display the banner and allow password auth
RUN echo "Banner /etc/ssh/banner.txt" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Create flag file readable by student
RUN echo "OCR{nse_scr1pt}" > /home/student/flag.txt && chown student:student /home/student/flag.txt

# Note: The flag appears in NSE script output when scanning with:
# nmap -p 22 --script=ssh-auth-methods <target>
# or
# nmap -p 22 --script="ssh*" <target>
# The banner is shown by the ssh2-enum-algos or banner NSE scripts

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]
