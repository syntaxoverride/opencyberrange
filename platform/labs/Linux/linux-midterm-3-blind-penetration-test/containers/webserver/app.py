"""
Apex Meridian Group. Corporate Web Server

A deliberately vulnerable Flask application with directory traversal on /download.
The config directory contains SSH credentials for the backend server and an
assessment marker.
"""

import os
from flask import Flask, request, abort

app = Flask(__name__)

DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #fafafa; color: #1a1a2e; }
    .nav { background: #1a1a2e; padding: 15px 40px; display: flex; align-items: center;
           gap: 30px; border-bottom: 3px solid #e94560; }
    .nav .brand { color: #e94560; font-weight: bold; font-size: 1.2em; margin-right: auto;
                  text-decoration: none; letter-spacing: 2px; }
    .nav a { color: #a0a0b8; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #e94560; }
    .hero { background: linear-gradient(135deg, #1a1a2e 0%%, #16213e 50%%, #0f3460 100%%);
            padding: 80px 40px; text-align: center; border-bottom: 3px solid #e94560; }
    .hero h1 { color: #e94560; font-size: 2.8em; letter-spacing: 3px; margin-bottom: 15px; }
    .hero p { color: #a0a0b8; font-size: 1.15em; max-width: 650px; margin: 0 auto; }
    .content { max-width: 960px; margin: 40px auto; padding: 0 20px; }
    .card { background: #ffffff; border-radius: 8px; padding: 30px; margin: 20px 0;
            border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .card h2 { color: #1a1a2e; margin-bottom: 15px; }
    .card p { line-height: 1.7; color: #555; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .footer { text-align: center; padding: 30px; color: #888; font-size: 0.8em;
              border-top: 1px solid #e0e0e0; margin-top: 60px; }
    .footer a { color: #e94560; text-decoration: none; }
    pre { background: #1a1a2e; color: #4ade80; padding: 15px; border-radius: 4px;
          overflow-x: auto; font-size: 0.9em; }
    ul { padding-left: 20px; }
    li { margin: 8px 0; }
    a.dl { color: #0f3460; text-decoration: underline; }
    a.dl:hover { color: #e94560; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">APEX MERIDIAN GROUP</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/services">Services</a>
    <a href="/resources">Resources</a>
    <a href="/contact">Contact</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 Apex Meridian Group, LLC. All rights reserved.<br>
    <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a> &bull;
    <a href="/careers">Careers</a><br>
    Charlotte, NC &bull; Raleigh, NC &bull; Atlanta, GA &bull; Nashville, TN
</div>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Apex Meridian Group</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>APEX MERIDIAN GROUP</h1>
    <p>Management Consulting &bull; Digital Transformation &bull; Strategic Advisory</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Operational Excellence</h2>
            <p>We help mid-market enterprises streamline operations, reduce costs,
            and build scalable processes that drive measurable results.</p>
        </div>
        <div class="card">
            <h2>Technology Advisory</h2>
            <p>Navigate complex technology decisions with confidence. From cloud
            migration to ERP selection, our advisors guide every step.</p>
        </div>
        <div class="card">
            <h2>M&amp;A Due Diligence</h2>
            <p>Comprehensive operational and technology due diligence for mergers,
            acquisitions, and private equity portfolio companies.</p>
        </div>
    </div>
    <div class="card">
        <h2>Trusted by Southeast Leaders</h2>
        <p>Over 150 companies across the Southeast rely on Apex Meridian Group for
        strategic guidance. From manufacturing to financial services, we deliver
        results that matter. Learn more about our <a href="/resources" style="color:#e94560;">resources and documentation</a>.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - Apex Meridian Group</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>About Apex Meridian Group</h2>
        <p>Founded in 2016, Apex Meridian Group was established by a team of former
        Big Four consultants who saw an underserved market: mid-size companies in
        the Southeast that needed world-class advisory without the overhead of a
        global firm. Our Charlotte headquarters anchors a regional practice spanning
        four offices and 280+ professionals.</p>
        <br>
        <p>We specialize in three areas: operational strategy, technology transformation,
        and regulatory compliance. Our clients range from $50M to $2B in revenue,
        spanning manufacturing, healthcare, financial services, and logistics.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>Daniel Reeves</strong>. Director of IT<br>
        <strong>Catherine Marsh</strong>. Managing Partner<br>
        <strong>James Whitford</strong>. Partner, Technology Practice<br>
        <strong>Priya Narayanan</strong>. Partner, Operations Practice<br>
        <strong>Robert Liang</strong>. CFO</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/services")
def services():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Services - Apex Meridian Group</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Our Services</h2>
        <p>Apex Meridian Group offers a full spectrum of consulting services tailored
        to the needs of mid-market enterprises. Every engagement is led by a senior
        partner with deep industry expertise.</p>
    </div>
    <div class="grid">
        <div class="card">
            <h2>Strategic Advisory</h2>
            <p>Market analysis, competitive positioning, growth strategy, and
            board-level advisory services.</p>
        </div>
        <div class="card">
            <h2>Process Improvement</h2>
            <p>Lean Six Sigma methodology, workflow optimization, and
            organizational design for operational efficiency.</p>
        </div>
        <div class="card">
            <h2>Digital Transformation</h2>
            <p>Cloud migration, ERP implementation, data analytics strategy,
            and cybersecurity posture assessment.</p>
        </div>
        <div class="card">
            <h2>Compliance &amp; Risk</h2>
            <p>SOC 2 readiness, HIPAA compliance, CMMC preparation, and
            enterprise risk management frameworks.</p>
        </div>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/resources")
def resources():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Resources - Apex Meridian Group</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Resources &amp; Documentation</h2>
        <p>Download our latest publications, brochures, and pricing guides.</p>
        <ul style="margin-top:15px;">
            <li><a class="dl" href="/download?file=brochure.txt">Corporate Brochure</a>. Company overview and practice areas</li>
            <li><a class="dl" href="/download?file=pricing.txt">Service Pricing Guide</a>. Engagement models and fee structures</li>
        </ul>
        <p style="margin-top:20px; color:#888; font-size:0.85em;">
            Additional documents are available upon request. Contact your account manager
            for access to engagement-specific deliverables.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/contact")
def contact():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Contact - Apex Meridian Group</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Contact Us</h2>
        <p><strong>Headquarters:</strong> 400 S Tryon Street, Suite 1200, Charlotte, NC 28202<br>
        <strong>Phone:</strong> (704) 555-0192<br>
        <strong>Email:</strong> info@apexmeridian.com</p>
        <br>
        <p><strong>Regional Offices:</strong></p>
        <p>Raleigh, NC &bull; Atlanta, GA &bull; Nashville, TN</p>
        <br>
        <p style="color:#888; font-size:0.85em;">For IT support or system access
        requests, contact Daniel Reeves at d.reeves@apexmeridian.com.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


# ========================================================================
# /download. VULNERABLE to directory traversal
# ========================================================================

@app.route("/download")
def download():
    filename = request.args.get("file", "")
    if not filename:
        abort(400, "Missing file parameter")

    # VULNERABLE: No sanitization of path traversal sequences
    filepath = os.path.join(DOC_ROOT, filename)

    try:
        with open(filepath, "r") as f:
            content = f.read()
        return content, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except FileNotFoundError:
        abort(404, "File not found")
    except IsADirectoryError:
        abort(400, "Cannot download a directory")
    except PermissionError:
        abort(403, "Permission denied")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
