FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y openssh-server python3 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash admin && echo "admin:password123" | chpasswd
RUN echo "OCR{w1nrm_d3t3ct}" > /home/admin/flag.txt
RUN mkdir /var/run/sshd

# Create WinRM simulation HTTP servers on ports 5985 and 5986
# These servers respond with headers that make nmap identify them as Microsoft HTTPAPI
RUN printf '#!/usr/bin/env python3\n\
import http.server\n\
import socketserver\n\
import sys\n\
\n\
class WinRMHandler(http.server.SimpleHTTPRequestHandler):\n\
    def do_GET(self):\n\
        self.send_response(200)\n\
        self.send_header("Content-Type", "application/soap+xml")\n\
        self.send_header("Server", "Microsoft-HTTPAPI/2.0")\n\
        self.send_header("WWW-Authenticate", "Negotiate")\n\
        self.end_headers()\n\
        self.wfile.write(b"<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>")\n\
    def log_message(self, format, *args):\n\
        pass\n\
\n\
if __name__ == "__main__":\n\
    port = int(sys.argv[1])\n\
    with socketserver.TCPServer(("", port), WinRMHandler) as httpd:\n\
        httpd.serve_forever()\n\
' > /usr/local/bin/winrm-simulator.py && chmod +x /usr/local/bin/winrm-simulator.py

# Create startup script to run all services
RUN printf '#!/bin/bash\n\
/usr/sbin/sshd -D &\n\
python3 /usr/local/bin/winrm-simulator.py 5985 &\n\
python3 /usr/local/bin/winrm-simulator.py 5986 &\n\
wait -n\n\
exit $?\n\
' > /start-services.sh && chmod +x /start-services.sh

EXPOSE 22 5985 5986
CMD ["/start-services.sh"]
