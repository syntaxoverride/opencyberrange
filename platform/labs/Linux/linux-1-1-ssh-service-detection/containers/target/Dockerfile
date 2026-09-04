FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install paramiko
RUN pip3 install --no-cache-dir paramiko cryptography

# Create SSH directory
RUN mkdir -p /opt/ssh-server

# Copy the SSH server script
COPY ssh_server.py /opt/ssh-server/ssh_server.py
RUN chmod +x /opt/ssh-server/ssh_server.py

# Generate host key
RUN python3 -c "import paramiko; key = paramiko.RSAKey.generate(2048); key.write_private_key_file('/opt/ssh-server/host_rsa_key')"

# Create flag file
RUN echo "OCR{ssh_d3t3ct3d}" > /root/flag.txt

EXPOSE 22

CMD ["python3", "-u", "/opt/ssh-server/ssh_server.py"]
