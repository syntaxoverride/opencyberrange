"""Cascade Digital Media. Content Platform (vulnerable to directory traversal)"""

from flask import Flask, request, send_file, abort
import os

app = Flask(__name__)

MEDIA_DIR = "/app/media/assets"
DOCS_DIR = "/app/docs"
REPORTS_DIR = "/app/api/reports"

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f4f8; color: #333; }
    .nav { background: #1a365d; padding: 15px 30px; display: flex; align-items: center; gap: 25px; }
    .nav .brand { color: #63b3ed; font-weight: bold; font-size: 1.15em; margin-right: auto;
                  text-decoration: none; letter-spacing: 1px; }
    .nav a { color: #a0aec0; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #fff; }
    .hero { background: linear-gradient(135deg, #1a365d 0%, #2a4365 100%);
            padding: 50px 30px; text-align: center; border-bottom: 3px solid #63b3ed; }
    .hero h1 { color: #fff; font-size: 2em; margin-bottom: 10px; }
    .hero p { color: #a0aec0; font-size: 1.05em; }
    .content { max-width: 900px; margin: 30px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 8px; padding: 25px; margin: 15px 0;
            box-shadow: 0 1px 5px rgba(0,0,0,0.1); }
    .card h2 { color: #1a365d; margin-bottom: 15px; font-size: 1.2em; }
    .card p { line-height: 1.6; color: #4a5568; }
    a { color: #3182ce; text-decoration: none; }
    a:hover { text-decoration: underline; }
    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
    th { color: #718096; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em;
             font-weight: bold; }
    .badge-img { background: #fed7d7; color: #9b2c2c; }
    .badge-txt { background: #c6f6d5; color: #276749; }
    .badge-csv { background: #bee3f8; color: #2a4365; }
    .badge-doc { background: #fefcbf; color: #744210; }
    .footer { text-align: center; padding: 25px; color: #a0aec0; font-size: 0.8em;
              border-top: 1px solid #e2e8f0; margin-top: 40px; }
    .footer a { color: #63b3ed; }
    .breadcrumb { color: #718096; font-size: 0.85em; margin-bottom: 15px; }
    .breadcrumb a { color: #3182ce; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">Cascade Digital Media</a>
    <a href="/">Media Library</a>
    <a href="/docs">Documentation</a>
    <a href="/api/reports">Reports</a>
    <a href="/about">About</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 Cascade Digital Media, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a> &bull;
    <a href="/about">About</a><br>
    Portland, OR &bull; Austin, TX &bull; New York, NY
</div>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Cascade Digital Media. Media Library</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>Media Library</h1>
    <p>Download brand assets, campaign archives, and media resources</p>
</div>
<div class="content">
    <div class="card">
        <h2>Available Media Assets</h2>
        <p style="color:#718096; margin-bottom:15px;">Browse and download media files from the Cascade asset repository.</p>
        <table>
            <tr><th>Asset</th><th>Category</th><th>Format</th><th>Action</th></tr>
            <tr><td>Brand Kit</td><td>Branding</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/media/download?asset=brand_kit.txt">Download</a></td></tr>
            <tr><td>Campaign Archive Q3</td><td>Marketing</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/media/download?asset=campaign_q3.txt">Download</a></td></tr>
            <tr><td>Photo Library Index</td><td>Creative</td>
                <td><span class="badge badge-txt">TXT</span></td>
                <td><a href="/media/download?asset=photo_index.txt">Download</a></td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Other Resources</h2>
        <p>
            <a href="/docs">Internal Documentation</a> &bull;
            <a href="/api/reports">Analytics & Reports</a> &bull;
            <a href="/about">About Cascade</a>
        </p>
    </div>

    <div class="card">
        <h2>About Cascade Digital Media</h2>
        <p>Cascade Digital Media is a full-service digital content agency specializing in
        brand storytelling, campaign management, and audience analytics. Founded in 2018,
        we partner with over 200 brands across retail, technology, and entertainment to
        deliver data-driven content strategies that drive measurable results.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/docs")
def docs_page():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Cascade Digital Media. Documentation</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="breadcrumb"><a href="/">Home</a> / Documentation</div>
    <div class="card">
        <h2>Internal Documentation</h2>
        <p style="color:#718096; margin-bottom:15px;">Company guides, style references, and technical documentation for the Cascade team.</p>
        <table>
            <tr><th>Document</th><th>Category</th><th>Format</th><th>Action</th></tr>
            <tr><td>Employee Onboarding Guide</td><td>HR</td>
                <td><span class="badge badge-doc">DOC</span></td>
                <td><a href="/docs/fetch?doc=onboarding.txt">Fetch</a></td></tr>
            <tr><td>Content Style Guide v2.3</td><td>Editorial</td>
                <td><span class="badge badge-doc">DOC</span></td>
                <td><a href="/docs/fetch?doc=style_guide.txt">Fetch</a></td></tr>
            <tr><td>Platform Architecture</td><td>Engineering</td>
                <td><span class="badge badge-doc">DOC</span></td>
                <td><a href="/docs/fetch?doc=architecture.txt">Fetch</a></td></tr>
        </table>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/api/reports")
def reports_page():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Cascade Digital Media. Reports</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="breadcrumb"><a href="/">Home</a> / Reports</div>
    <div class="card">
        <h2>Analytics & Revenue Reports</h2>
        <p style="color:#718096; margin-bottom:15px;">Export analytics dashboards and financial summaries.</p>
        <table>
            <tr><th>Report</th><th>Period</th><th>Format</th><th>Action</th></tr>
            <tr><td>Monthly Analytics</td><td>October 2024</td>
                <td><span class="badge badge-csv">CSV</span></td>
                <td><a href="/api/export?report=analytics_oct.txt">Export</a></td></tr>
            <tr><td>Revenue Summary</td><td>Q3 2024</td>
                <td><span class="badge badge-csv">CSV</span></td>
                <td><a href="/api/export?report=revenue_q3.txt">Export</a></td></tr>
        </table>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About. Cascade Digital Media</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>About Cascade Digital Media</h2>
        <p>Cascade Digital Media was founded in 2018 in Portland, Oregon. We are a
        digital content agency helping brands tell their stories through data-driven
        creative strategies.</p>
        <br>
        <p><strong>Leadership:</strong><br>
        Jordan Blake. VP of Engineering<br>
        Mira Patel. Director of Content Strategy<br>
        Ethan Cross. Head of Analytics<br>
        Leah Nguyen. Chief Creative Officer</p>
        <br>
        <p><strong>Contact:</strong><br>
        General: hello@cascadedigital.media<br>
        Engineering: engineering@cascadedigital.media<br>
        Phone: (503) 555-0142</p>
    </div>
</div>
{FOOTER}
</body></html>"""


# ── Endpoint 1: Media download (serves from /app/media/assets) ───────
@app.route("/media/download")
def media_download():
    filename = request.args.get("asset", "")
    if not filename:
        abort(400, "Missing asset parameter")

    # VULNERABLE: No path sanitization. allows directory traversal
    filepath = os.path.join(MEDIA_DIR, filename)

    try:
        return send_file(filepath, as_attachment=False)
    except FileNotFoundError:
        abort(404, f"Asset not found: {filename}")
    except Exception:
        abort(500, "Internal server error")


# ── Endpoint 2: Docs fetch (serves from /app/docs/files) ────────────
@app.route("/docs/fetch")
def docs_fetch():
    filename = request.args.get("doc", "")
    if not filename:
        abort(400, "Missing doc parameter")

    # VULNERABLE: No path sanitization. allows directory traversal
    filepath = os.path.join(DOCS_DIR, filename)

    try:
        return send_file(filepath, as_attachment=False)
    except FileNotFoundError:
        abort(404, f"Document not found: {filename}")
    except Exception:
        abort(500, "Internal server error")


# ── Endpoint 3: API export (serves from /app/api/reports) ────────────
@app.route("/api/export")
def api_export():
    filename = request.args.get("report", "")
    if not filename:
        abort(400, "Missing report parameter")

    # VULNERABLE: No path sanitization. allows directory traversal
    filepath = os.path.join(REPORTS_DIR, filename)

    try:
        return send_file(filepath, as_attachment=False)
    except FileNotFoundError:
        abort(404, f"Report not found: {filename}")
    except Exception:
        abort(500, "Internal server error")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
