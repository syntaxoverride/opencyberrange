#!/usr/bin/env python3
"""Meridian Trust Bank. Core Banking API (simulated)."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

API_KEY = "MTB_k3y_h0p_l4t3r4l"
LISTEN_PORT = 8080


class MeridianAPIHandler(BaseHTTPRequestHandler):
    """Handle requests to the core banking API."""

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/vault":
            key = self.headers.get("X-API-Key", "")
            if key != API_KEY:
                self._send_json(401, {"error": "API key required"})
            else:
                self._send_json(200, {
                    "vault": "meridian-core-banking",
                    "assessment_token": "l4t3r4l",
                    "timestamp": "2024-09-12T14:30:00Z"
                })

        else:
            self._send_json(404, {"error": "not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), MeridianAPIHandler)
    print(f"Meridian Core API listening on port {LISTEN_PORT}")
    server.serve_forever()
