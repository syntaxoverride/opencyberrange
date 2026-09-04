#!/usr/bin/env python3
import http.server
import socketserver
import sys

class WinRMHandler(http.server.SimpleHTTPRequestHandler):
    server_version = "Microsoft-HTTPAPI/2.0"
    sys_version = ""
    def _send_winrm_response(self, include_body=True):
        self.send_response(200)
        self.send_header("Content-Type", "application/soap+xml")
        self.send_header("WWW-Authenticate", "Negotiate")
        self.end_headers()
        if include_body:
            self.wfile.write(b'<?xml version="1.0" encoding="UTF-8"?>')
    def do_GET(self):
        self._send_winrm_response(True)
    def do_HEAD(self):
        self._send_winrm_response(False)
    def do_POST(self):
        self._send_winrm_response(True)
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(sys.argv[1])
    with socketserver.TCPServer(("", port), WinRMHandler) as httpd:
        httpd.serve_forever()
