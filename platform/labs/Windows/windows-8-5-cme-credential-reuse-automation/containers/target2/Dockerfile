FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install xrdp for RDP service
RUN apt-get update && apt-get install -y xrdp xfce4 && rm -rf /var/lib/apt/lists/*

# Create user with credentials (same as target1 for credential reuse)
RUN useradd -m -s /bin/bash admin && echo "admin:password123" | chpasswd

# Configure xrdp
RUN echo "xfce4-session" > /home/admin/.xsession && \
    chown admin:admin /home/admin/.xsession && \
    chmod +x /home/admin/.xsession

# Create flag file
RUN echo "OCR{cme_rdp_cr3d3nt14l_t3st}" > /home/admin/flag.txt && \
    chown admin:admin /home/admin/flag.txt

EXPOSE 3389
CMD service xrdp start && tail -f /dev/null

