FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install SSH for WinRM-like access (simplified for Docker)
# In real scenarios, WinRM would be used, but SSH is easier in containers
RUN apt-get update && apt-get install -y openssh-server && rm -rf /var/lib/apt/lists/*

# Create user with same credentials (for credential reuse demonstration)
RUN useradd -m -s /bin/bash admin && echo "admin:password123" | chpasswd

# Create flag file
RUN echo "OCR{cme_ssh_cr3d3nt14l_t3st}" > /home/admin/flag.txt && \
    chown admin:admin /home/admin/flag.txt

# Configure SSH
RUN mkdir /var/run/sshd && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]

