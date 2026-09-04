"""
Vertex Healthcare. Patient Portal Web Application

A deliberately vulnerable Flask application for the SQL Injection to Shell lab.
The login form uses string formatting for SQL queries (NOT parameterized),
making it vulnerable to UNION-based SQL injection.
"""

import time
import MySQLdb
from flask import Flask, request, redirect, make_response

app = Flask(__name__)

DB_HOST = "vertex-db"
DB_USER = "vtx_app"
DB_PASS = "Vtx_App_2024#"
DB_NAME = "vertex_portal"


def get_db():
    """Get a MySQL database connection with retry logic for startup."""
    for attempt in range(30):
        try:
            conn = MySQLdb.connect(
                host=DB_HOST, user=DB_USER, passwd=DB_PASS, db=DB_NAME
            )
            return conn
        except MySQLdb.OperationalError:
            if attempt < 29:
                time.sleep(2)
    return None


# ═══════════════════════════════════════════════════════════════════════
# Styles
# ═══════════════════════════════════════════════════════════════════════

STYLE = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8f9fa; color: #333; }
    .nav { background: #0d2137; padding: 15px 40px; display: flex; align-items: center; gap: 30px; }
    .nav a { color: #8faabe; text-decoration: none; font-size: 0.95em; }
    .nav a:hover { color: #fff; }
    .nav .brand { color: #26c6da; font-weight: bold; font-size: 1.2em; margin-right: auto; }
    .hero { background: linear-gradient(135deg, #0d2137 0%, #1a3a5c 50%, #0d4f6e 100%);
            padding: 80px 40px; text-align: center; color: #fff; }
    .hero h1 { font-size: 2.8em; margin-bottom: 15px; }
    .hero p { font-size: 1.2em; color: #80d8e4; max-width: 600px; margin: 0 auto; }
    .content { max-width: 960px; margin: 40px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 10px; padding: 30px; margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
    .card h2 { color: #0d2137; margin-bottom: 15px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .footer { text-align: center; padding: 30px; color: #888; font-size: 0.85em;
              border-top: 1px solid #e0e0e0; margin-top: 60px; }
    .footer a { color: #26c6da; text-decoration: none; }
    /* Portal styles */
    .login-container { max-width: 400px; margin: 80px auto; }
    .login-box { background: #fff; border-radius: 10px; padding: 40px;
                 box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
    .login-box h2 { text-align: center; color: #0d2137; margin-bottom: 25px; }
    .login-box input { width: 100%%; padding: 12px; margin: 8px 0; border: 1px solid #ddd;
                       border-radius: 6px; font-size: 1em; }
    .login-box button { width: 100%%; padding: 12px; background: #26c6da; color: #fff;
                        border: none; border-radius: 6px; font-size: 1em; cursor: pointer;
                        margin-top: 15px; }
    .login-box button:hover { background: #00acc1; }
    .error { color: #e74c3c; text-align: center; margin-bottom: 15px; font-size: 0.9em; }
    .dash-header { background: #0d2137; color: #fff; padding: 20px 40px; }
    .dash-header h1 { font-size: 1.4em; }
    .dash-header span { color: #26c6da; }
    .dash-body { max-width: 960px; margin: 30px auto; padding: 0 20px; }
    table { width: 100%%; border-collapse: collapse; }
    table th { background: #f1f3f5; padding: 12px; text-align: left; font-size: 0.85em;
               color: #666; text-transform: uppercase; }
    table td { padding: 12px; border-bottom: 1px solid #eee; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.8em; }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .config-block { background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px;
                    padding: 15px; font-family: monospace; font-size: 0.85em; margin: 15px 0;
                    white-space: pre-wrap; color: #333; }
</style>
"""

NAV = """
<nav class="nav">
    <a href="/" class="brand">Vertex Healthcare</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/services">Services</a>
    <a href="/contact">Contact</a>
</nav>
"""

FOOTER = """
<div class="footer">
    &copy; 2025 Vertex Healthcare, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy Policy</a> &bull; <a href="/terms">Terms of Service</a><br>
    Denver, CO &bull; Phoenix, AZ &bull; Salt Lake City, UT
</div>
"""


# ═══════════════════════════════════════════════════════════════════════
# Public pages
# ═══════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Vertex Healthcare</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>Vertex Healthcare</h1>
    <p>EHR integration &bull; Clinical data platforms &bull; HIPAA-compliant solutions</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>EHR Integration</h2>
            <p>Seamless electronic health record integration across hospital systems,
            clinics, and specialty practices. HL7 FHIR compliant.</p>
        </div>
        <div class="card">
            <h2>Clinical Analytics</h2>
            <p>Real-time dashboards and predictive analytics to improve patient outcomes
            and optimize clinical workflows across your network.</p>
        </div>
        <div class="card">
            <h2>Compliance &amp; Security</h2>
            <p>End-to-end HIPAA compliance, SOC 2 certified infrastructure, and
            24/7 security monitoring for all patient data.</p>
        </div>
    </div>
    <div class="card">
        <h2>Trusted by Healthcare Providers</h2>
        <p>Vertex Healthcare serves over 40 clinics and hospitals across the western
        United States. Our platform processes 2 million+ patient records daily with
        99.99%% uptime.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - Vertex Healthcare</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>About Vertex Healthcare</h2>
        <p>Founded in 2018 by Dr. Marcus Webb and Rachel Nguyen, Vertex Healthcare
        began as a health IT consultancy focused on EHR interoperability. Seven years
        later, we are a team of 120 engineers, clinicians, and data scientists serving
        healthcare providers across the western United States.</p>
        <br>
        <p>Our mission is to break down data silos in healthcare. We believe that
        connected clinical data saves lives, reduces costs, and empowers providers
        to deliver better patient care.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>Dr. Marcus Webb</strong>. CEO &amp; Co-Founder<br>
        <strong>Rachel Nguyen</strong>. Director of IT Security<br>
        <strong>David Park</strong>. VP of Engineering<br>
        <strong>Lisa Chen</strong>. Chief Medical Officer</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/services")
def services():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Services - Vertex Healthcare</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Our Services</h2>
        <ul style="line-height: 2; padding-left: 20px;">
            <li>EHR System Integration (Epic, Cerner, Allscripts)</li>
            <li>HL7 FHIR API Development</li>
            <li>Clinical Data Warehouse Design</li>
            <li>Patient Portal Development</li>
            <li>HIPAA Compliance Auditing</li>
            <li>Healthcare Analytics &amp; Reporting</li>
            <li>Telehealth Platform Engineering</li>
            <li>Medical IoT Device Integration</li>
        </ul>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/contact")
def contact():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Contact - Vertex Healthcare</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Get in Touch</h2>
        <p><strong>Headquarters:</strong> 1700 Lincoln St, Suite 3200, Denver, CO 80203<br>
        <strong>Phone:</strong> (303) 555-0142<br>
        <strong>Email:</strong> info@vertexhealthcare.com<br>
        <strong>Sales:</strong> sales@vertexhealthcare.com</p>
        <br>
        <p><strong>Phoenix Office:</strong> 2 N Central Ave, Suite 1800, Phoenix, AZ 85004<br>
        <strong>Salt Lake City Office:</strong> 111 S Main St, Suite 2600, Salt Lake City, UT 84111</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Disallow: /portal/
Disallow: /api/internal/
Disallow: /backups/
""", 200, {"Content-Type": "text/plain"}


# ═══════════════════════════════════════════════════════════════════════
# Decoy endpoints
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/internal/")
def api_internal():
    return '{"error":"unauthorized","message":"API key required"}', 401, \
           {"Content-Type": "application/json"}

@app.route("/backups/")
def backups():
    return "403 Forbidden", 403


# ═══════════════════════════════════════════════════════════════════════
# Patient Portal (hidden. discovered via robots.txt)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/portal/")
def portal_login():
    error_msg = ""
    if request.args.get("error"):
        error_msg = '<p class="error">Invalid username or password. Please try again.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vertex Healthcare - Provider Portal</title>
    {STYLE}
</head>
<body style="background: #0d2137;">
<div class="login-container">
    <div class="login-box">
        <h2>Vertex Provider Portal</h2>
        {error_msg}
        <form method="POST" action="/portal/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <p style="text-align: center; margin-top: 20px; font-size: 0.8em; color: #999;">
            Authorized personnel only. Contact IT for access.
        </p>
    </div>
</div>
</body></html>"""


@app.route("/portal/login", methods=["POST"])
def portal_do_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # ── VULNERABLE: SQL query built with string formatting ──────────
    # This is intentionally vulnerable to SQL injection for the lab.
    # The password check is entirely in the WHERE clause. if the query
    # returns any row, the application considers the login successful.
    query = f"SELECT id, username, password, email FROM users WHERE username='{username}' AND password='{password}'"

    try:
        conn = get_db()
        if conn is None:
            return "Database unavailable", 503

        cursor = conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            resp = make_response(redirect("/portal/dashboard"))
            resp.set_cookie("vtx_session", "authenticated_portal_v4")
            return resp

        return redirect("/portal/?error=1")

    except Exception:
        return redirect("/portal/?error=1")


@app.route("/portal/dashboard")
def portal_dashboard():
    if request.cookies.get("vtx_session") != "authenticated_portal_v4":
        return redirect("/portal/")

    # Assessment token 1 (sql1_un10n) is displayed as the assessment_token
    # Database credentials are shown in the configuration panel
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Provider Dashboard - Vertex Healthcare</title>{STYLE}</head>
<body>
<div class="dash-header">
    <h1>Vertex <span>Provider Dashboard</span></h1>
</div>
<div class="dash-body">
    <div class="card">
        <h2>System Status</h2>
        <table>
            <tr><th>Component</th><th>Status</th><th>Value</th></tr>
            <tr><td>Web Application</td><td><span class="badge badge-green">Online</span></td><td>v4.1.0</td></tr>
            <tr><td>Database</td><td><span class="badge badge-green">Connected</span></td><td>MySQL 8.0</td></tr>
            <tr><td>Assessment Token</td><td><span class="badge badge-yellow">Active</span></td><td><code>sql1_un10n</code></td></tr>
            <tr><td>FHIR Gateway</td><td><span class="badge badge-green">Online</span></td><td>R4 v4.0.1</td></tr>
            <tr><td>Audit Logger</td><td><span class="badge badge-green">Running</span></td><td>6 streams</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Provider Quick Links</h2>
        <ul style="line-height: 2; padding-left: 20px;">
            <li>Patient Records (EHR Access)</li>
            <li>Lab Results Portal</li>
            <li>Prescription Management</li>
            <li>Clinical Scheduling System</li>
        </ul>
    </div>

    <div class="card">
        <h2>Application Configuration</h2>
        <p style="color: #888; font-size: 0.9em;">Current production environment settings:</p>
        <div class="config-block">APP_ENV=production
APP_VERSION=4.1.0
DB_HOST=vertex-db
DB_PORT=3306
DB_NAME=vertex_portal
DB_USER=vtx_admin
DB_PASS=Vtx_DB_R00t#
FHIR_ENDPOINT=https://fhir.vertexhealthcare.com/r4
AUDIT_LOG_LEVEL=info</div>
        <p style="color: #e74c3c; font-size: 0.8em; margin-top: 10px;">
            &#9888; This configuration panel should be restricted in production. See JIRA-VTX-892.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
# Catch-all and utility routes
# ═══════════════════════════════════════════════════════════════════════

@app.route("/admin")
@app.route("/admin/")
def admin_redirect():
    return redirect("/portal/")

@app.route("/login")
@app.route("/login/")
def login_redirect():
    return redirect("/portal/")

@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html><head><title>Privacy - Vertex Healthcare</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Privacy Policy</h2><p>Vertex Healthcare is committed to protecting patient
privacy in accordance with HIPAA regulations. This policy outlines how we collect,
use, and safeguard protected health information (PHI).</p>
</div></div>{FOOTER}</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html><head><title>Terms - Vertex Healthcare</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Terms of Service</h2><p>By using Vertex Healthcare services, you agree to the
following terms and conditions governing the use of our clinical data platform.</p>
</div></div>{FOOTER}</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
