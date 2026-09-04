"""
MedCore Health Systems. Clinical Data Platform Web Application

A deliberately vulnerable Flask application for the Full Web-to-Root lab.
The admin portal login form uses string formatting for SQL queries (NOT
parameterized), making it vulnerable to UNION-based SQL injection.
"""

import time
import MySQLdb
from flask import Flask, request, redirect, make_response

app = Flask(__name__)

DB_HOST = "medcore-db"
DB_USER = "mdc_app"
DB_PASS = "Mdc_App_2025#"
DB_NAME = "medcore"


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
    .nav { background: #1b2a4a; padding: 15px 40px; display: flex; align-items: center; gap: 30px; }
    .nav a { color: #8fa4c8; text-decoration: none; font-size: 0.95em; }
    .nav a:hover { color: #fff; }
    .nav .brand { color: #42a5f5; font-weight: bold; font-size: 1.2em; margin-right: auto; }
    .hero { background: linear-gradient(135deg, #1b2a4a 0%, #263d5e 50%, #1a4971 100%);
            padding: 80px 40px; text-align: center; color: #fff; }
    .hero h1 { font-size: 2.8em; margin-bottom: 15px; }
    .hero p { font-size: 1.2em; color: #90caf9; max-width: 600px; margin: 0 auto; }
    .content { max-width: 960px; margin: 40px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 10px; padding: 30px; margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
    .card h2 { color: #1b2a4a; margin-bottom: 15px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .footer { text-align: center; padding: 30px; color: #888; font-size: 0.85em;
              border-top: 1px solid #e0e0e0; margin-top: 60px; }
    .footer a { color: #42a5f5; text-decoration: none; }
    /* Admin portal styles */
    .login-container { max-width: 400px; margin: 80px auto; }
    .login-box { background: #fff; border-radius: 10px; padding: 40px;
                 box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
    .login-box h2 { text-align: center; color: #1b2a4a; margin-bottom: 25px; }
    .login-box input { width: 100%%; padding: 12px; margin: 8px 0; border: 1px solid #ddd;
                       border-radius: 6px; font-size: 1em; }
    .login-box button { width: 100%%; padding: 12px; background: #42a5f5; color: #fff;
                        border: none; border-radius: 6px; font-size: 1em; cursor: pointer;
                        margin-top: 15px; }
    .login-box button:hover { background: #1e88e5; }
    .error { color: #e74c3c; text-align: center; margin-bottom: 15px; font-size: 0.9em; }
    .dash-header { background: #1b2a4a; color: #fff; padding: 20px 40px; }
    .dash-header h1 { font-size: 1.4em; }
    .dash-header span { color: #42a5f5; }
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
    <a href="/" class="brand">MedCore Health Systems</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/services">Services</a>
    <a href="/contact">Contact</a>
</nav>
"""

FOOTER = """
<div class="footer">
    &copy; 2025 MedCore Health Systems, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy Policy</a> &bull; <a href="/terms">Terms of Service</a><br>
    Portland, OR &bull; Seattle, WA &bull; Boise, ID
</div>
"""


# ═══════════════════════════════════════════════════════════════════════
# Public pages
# ═══════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>MedCore Health Systems</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>MedCore Health Systems</h1>
    <p>Clinical data exchange &bull; EHR interoperability &bull; HITRUST certified</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Data Exchange Platform</h2>
            <p>Real-time clinical data exchange between hospitals, clinics, and
            specialty practices. HL7 FHIR and CDA compliant.</p>
        </div>
        <div class="card">
            <h2>Analytics Engine</h2>
            <p>Population health analytics and predictive modeling to improve
            patient outcomes across your provider network.</p>
        </div>
        <div class="card">
            <h2>Compliance Suite</h2>
            <p>HITRUST CSF certified, HIPAA compliant, and SOC 2 Type II audited.
            End-to-end security for protected health information.</p>
        </div>
    </div>
    <div class="card">
        <h2>Trusted by Regional Health Networks</h2>
        <p>MedCore connects over 60 healthcare facilities across the Pacific Northwest.
        Our platform processes 3.5 million+ clinical transactions daily with 99.99%%
        uptime and sub-second data retrieval.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - MedCore Health Systems</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>About MedCore</h2>
        <p>Founded in 2019 by Dr. Sarah Okafor and Kevin Tran, MedCore Health Systems
        started as a health IT research lab at Oregon Health &amp; Science University.
        Six years later, we are a team of 95 engineers, clinicians, and data scientists
        building the infrastructure that connects Pacific Northwest healthcare.</p>
        <br>
        <p>Our mission is to eliminate data silos in regional healthcare. When a patient
        moves between providers, their clinical history should follow them seamlessly.
        MedCore makes that possible.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>Dr. Sarah Okafor</strong>. CISO &amp; Co-Founder<br>
        <strong>Kevin Tran</strong>. CTO &amp; Co-Founder<br>
        <strong>Maria Santos</strong>. VP of Engineering<br>
        <strong>Dr. James Liu</strong>. Chief Medical Officer</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/services")
def services():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Services - MedCore Health Systems</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Our Services</h2>
        <ul style="line-height: 2; padding-left: 20px;">
            <li>Clinical Data Exchange (HL7 FHIR R4)</li>
            <li>EHR Integration (Epic, Cerner, Meditech)</li>
            <li>Population Health Analytics</li>
            <li>Clinical Decision Support Systems</li>
            <li>HITRUST CSF Compliance Consulting</li>
            <li>Healthcare Data Warehouse Design</li>
            <li>Telehealth Infrastructure Engineering</li>
            <li>Medical Device Data Integration</li>
        </ul>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/contact")
def contact():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Contact - MedCore Health Systems</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Get in Touch</h2>
        <p><strong>Headquarters:</strong> 1120 NW Couch St, Suite 600, Portland, OR 97209<br>
        <strong>Phone:</strong> (503) 555-0193<br>
        <strong>Email:</strong> info@medcore-health.com<br>
        <strong>Sales:</strong> partnerships@medcore-health.com</p>
        <br>
        <p><strong>Seattle Office:</strong> 1201 3rd Ave, Suite 2200, Seattle, WA 98101<br>
        <strong>Boise Office:</strong> 800 W Main St, Suite 1400, Boise, ID 83702</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Disallow: /admin-portal/
Disallow: /api/v2/
Disallow: /staging/
""", 200, {"Content-Type": "text/plain"}


# ═══════════════════════════════════════════════════════════════════════
# Decoy endpoints
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/v2/")
def api_v2():
    return '{"error":"unauthorized","message":"Bearer token required"}', 401, \
           {"Content-Type": "application/json"}

@app.route("/staging/")
def staging():
    return "403 Forbidden", 403


# ═══════════════════════════════════════════════════════════════════════
# Admin Portal (hidden. discovered via robots.txt / directory enumeration)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/admin-portal/")
def admin_login():
    error_msg = ""
    if request.args.get("error"):
        error_msg = '<p class="error">Invalid username or password. Please try again.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MedCore Admin Portal</title>
    {STYLE}
</head>
<body style="background: #1b2a4a;">
<div class="login-container">
    <div class="login-box">
        <h2>MedCore Admin Portal</h2>
        {error_msg}
        <form method="POST" action="/admin-portal/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <p style="text-align: center; margin-top: 20px; font-size: 0.8em; color: #999;">
            Authorized personnel only. Contact IT Security for access.
        </p>
    </div>
</div>
</body></html>"""


@app.route("/admin-portal/login", methods=["POST"])
def admin_do_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # ── VULNERABLE: SQL query built with string formatting ──────────
    # This is intentionally vulnerable to SQL injection for the lab.
    # The password check is entirely in the WHERE clause. if the query
    # returns any row, the application considers the login successful.
    query = f"SELECT id, username, password, email, role FROM users WHERE username='{username}' AND password='{password}'"

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
            resp = make_response(redirect("/admin-portal/dashboard"))
            resp.set_cookie("mdc_session", "admin_authenticated_v3")
            return resp

        return redirect("/admin-portal/?error=1")

    except Exception:
        return redirect("/admin-portal/?error=1")


@app.route("/admin-portal/dashboard")
def admin_dashboard():
    if request.cookies.get("mdc_session") != "admin_authenticated_v3":
        return redirect("/admin-portal/")

    # Assessment token 1 (1nj3ct) displayed as the assessment marker
    # Database credentials shown in configuration panel
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Admin Dashboard - MedCore</title>{STYLE}</head>
<body>
<div class="dash-header">
    <h1>MedCore <span>Admin Dashboard</span></h1>
</div>
<div class="dash-body">
    <div class="card">
        <h2>System Status</h2>
        <table>
            <tr><th>Component</th><th>Status</th><th>Value</th></tr>
            <tr><td>Web Application</td><td><span class="badge badge-green">Online</span></td><td>v5.2.0</td></tr>
            <tr><td>Database</td><td><span class="badge badge-green">Connected</span></td><td>MySQL 8.0</td></tr>
            <tr><td>Assessment Marker</td><td><span class="badge badge-yellow">Active</span></td><td><code>1nj3ct</code></td></tr>
            <tr><td>FHIR Gateway</td><td><span class="badge badge-green">Online</span></td><td>R4 v4.0.1</td></tr>
            <tr><td>Data Processor</td><td><span class="badge badge-green">Running</span></td><td>8 workers</td></tr>
            <tr><td>Audit Logger</td><td><span class="badge badge-green">Running</span></td><td>12 streams</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Platform Quick Links</h2>
        <ul style="line-height: 2; padding-left: 20px;">
            <li>Patient Record Exchange Dashboard</li>
            <li>Provider Network Management</li>
            <li>Clinical Analytics Console</li>
            <li>Compliance Audit Reports</li>
        </ul>
    </div>

    <div class="card">
        <h2>Application Configuration</h2>
        <p style="color: #888; font-size: 0.9em;">Current production environment settings:</p>
        <div class="config-block">APP_ENV=production
APP_VERSION=5.2.0
DB_HOST=medcore-db
DB_PORT=3306
DB_NAME=medcore
DB_USER=mdc_admin
DB_PASS=Mdc_DB_Pr0d#2025
FHIR_ENDPOINT=https://fhir.medcore-health.com/r4
PROC_SERVER=medcore-proc
AUDIT_LOG_LEVEL=info</div>
        <p style="color: #e74c3c; font-size: 0.8em; margin-top: 10px;">
            &#9888; This configuration panel should be restricted in production. See JIRA-MDC-1247.</p>
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
    return redirect("/admin-portal/")

@app.route("/login")
@app.route("/login/")
def login_redirect():
    return redirect("/admin-portal/")

@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html><head><title>Privacy - MedCore</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Privacy Policy</h2><p>MedCore Health Systems is committed to protecting patient
privacy in accordance with HIPAA and HITRUST CSF requirements. This policy outlines
how we collect, use, and safeguard protected health information (PHI).</p>
</div></div>{FOOTER}</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html><head><title>Terms - MedCore</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Terms of Service</h2><p>By using MedCore Health Systems services, you agree to the
following terms and conditions governing the use of our clinical data platform.</p>
</div></div>{FOOTER}</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
