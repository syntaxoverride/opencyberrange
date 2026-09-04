"""Pinnacle Cloud Services. Documentation Portal (vulnerable to path traversal)"""

from flask import Flask, request, send_file, abort
import os

app = Flask(__name__)

DOC_DIR = "/app/docs"

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f4f8; color: #333; }
    .nav { background: #2d3748; padding: 15px 30px; display: flex; align-items: center; gap: 25px; }
    .nav .brand { color: #63b3ed; font-weight: bold; font-size: 1.15em; margin-right: auto;
                  text-decoration: none; letter-spacing: 1px; }
    .nav a { color: #a0aec0; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #fff; }
    .hero { background: linear-gradient(135deg, #2d3748 0%, #1a365d 100%);
            padding: 50px 30px; text-align: center; border-bottom: 3px solid #63b3ed; }
    .hero h1 { color: #fff; font-size: 2em; margin-bottom: 10px; }
    .hero p { color: #a0aec0; font-size: 1.05em; }
    .content { max-width: 900px; margin: 30px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 8px; padding: 25px; margin: 15px 0;
            box-shadow: 0 1px 5px rgba(0,0,0,0.1); }
    .card h2 { color: #2d3748; margin-bottom: 15px; font-size: 1.2em; }
    .card p { line-height: 1.6; color: #4a5568; }
    a { color: #3182ce; text-decoration: none; }
    a:hover { text-decoration: underline; }
    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
    th { color: #718096; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em;
             font-weight: bold; }
    .badge-pdf { background: #fed7d7; color: #9b2c2c; }
    .badge-txt { background: #c6f6d5; color: #276749; }
    .badge-doc { background: #bee3f8; color: #2a4365; }
    .footer { text-align: center; padding: 25px; color: #a0aec0; font-size: 0.8em;
              border-top: 1px solid #e2e8f0; margin-top: 40px; }
    .footer a { color: #63b3ed; }
    .breadcrumb { color: #718096; font-size: 0.85em; margin-bottom: 15px; }
    .breadcrumb a { color: #3182ce; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">Pinnacle Cloud</a>
    <a href="/">Documentation</a>
    <a href="/support">Support</a>
    <a href="/status">Status</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 Pinnacle Cloud Services, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a> &bull;
    <a href="/support">Support</a><br>
    San Jose, CA &bull; Portland, OR &bull; Raleigh, NC
</div>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Pinnacle Cloud Services. Documentation</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>Documentation Portal</h1>
    <p>Product guides, API references, and release notes for Pinnacle Cloud Services</p>
</div>
<div class="content">
    <div class="card">
        <h2>Product Documentation</h2>
        <p style="color:#718096; margin-bottom:15px;">Download product guides and technical references for Pinnacle Cloud Platform.</p>
        <table>
            <tr><th>Document</th><th>Category</th><th>Format</th><th>Action</th></tr>
            <tr><td>Getting Started Guide</td><td>Onboarding</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/download?file=getting_started.txt">Download</a></td></tr>
            <tr><td>API Reference v3.1</td><td>Developer</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/download?file=api_reference.txt">Download</a></td></tr>
            <tr><td>Release Notes. Q3 2024</td><td>Updates</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/download?file=release_notes.txt">Download</a></td></tr>
            <tr><td>Security Best Practices</td><td>Compliance</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/download?file=security_guide.txt">Download</a></td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Quick Links</h2>
        <p>
            <a href="/download?file=getting_started.txt">Quick Start</a> &bull;
            <a href="/download?file=api_reference.txt">API Docs</a> &bull;
            <a href="/support">Contact Support</a> &bull;
            <a href="/status">Service Status</a>
        </p>
    </div>

    <div class="card">
        <h2>About Pinnacle Cloud</h2>
        <p>Pinnacle Cloud Services provides scalable cloud infrastructure for startups and
        enterprises. Founded in 2017, we serve over 3,000 customers across North America with
        managed Kubernetes, object storage, serverless compute, and database-as-a-service offerings.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/support")
def support():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Support - Pinnacle Cloud</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Support</h2>
        <p><strong>Email:</strong> support@pinnacle-cloud.com<br>
        <strong>Phone:</strong> (408) 555-0173 (Mon-Fri, 6am-6pm PT)<br>
        <strong>Emergency:</strong> (408) 555-0199 (24/7 for critical outages)</p>
        <br>
        <p>For billing inquiries: billing@pinnacle-cloud.com<br>
        For partnership inquiries: partners@pinnacle-cloud.com</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/status")
def status():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Status - Pinnacle Cloud</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Service Status</h2>
        <p style="color:#276749; font-weight:bold;">All Systems Operational</p>
        <br>
        <p>Compute: <span style="color:#276749;">Operational</span><br>
        Object Storage: <span style="color:#276749;">Operational</span><br>
        Managed Kubernetes: <span style="color:#276749;">Operational</span><br>
        Database Service: <span style="color:#276749;">Operational</span><br>
        CDN: <span style="color:#276749;">Operational</span></p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/download")
def download():
    filename = request.args.get("file", "")
    if not filename:
        abort(400, "Missing file parameter")

    # VULNERABLE: No path sanitization. allows directory traversal
    filepath = os.path.join(DOC_DIR, filename)

    try:
        return send_file(filepath, as_attachment=False)
    except FileNotFoundError:
        abort(404, f"File not found: {filename}")
    except Exception:
        abort(500, "Internal server error")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
