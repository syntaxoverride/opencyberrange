"""
NovaTech Solutions. Corporate Web Application

A deliberately vulnerable Flask application for the Hidden Login Discovery lab.
Contains a hidden staff portal with default credentials and leaked DB config.
"""

from flask import Flask, request, redirect, make_response, url_for

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Public pages (visible, linked from navigation)
# ═══════════════════════════════════════════════════════════════════════

STYLE = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8f9fa; color: #333; }
    .nav { background: #1a1a2e; padding: 15px 40px; display: flex; align-items: center; gap: 30px; }
    .nav a { color: #a0a0c0; text-decoration: none; font-size: 0.95em; }
    .nav a:hover { color: #fff; }
    .nav .brand { color: #4fc3f7; font-weight: bold; font-size: 1.2em; margin-right: auto; }
    .hero { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 80px 40px; text-align: center; color: #fff; }
    .hero h1 { font-size: 2.8em; margin-bottom: 15px; }
    .hero p { font-size: 1.2em; color: #a0c4ff; max-width: 600px; margin: 0 auto; }
    .content { max-width: 960px; margin: 40px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 10px; padding: 30px; margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
    .card h2 { color: #1a1a2e; margin-bottom: 15px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .footer { text-align: center; padding: 30px; color: #888; font-size: 0.85em;
              border-top: 1px solid #e0e0e0; margin-top: 60px; }
    .footer a { color: #4fc3f7; text-decoration: none; }
    /* Staff portal styles */
    .login-container { max-width: 400px; margin: 80px auto; }
    .login-box { background: #fff; border-radius: 10px; padding: 40px;
                 box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
    .login-box h2 { text-align: center; color: #1a1a2e; margin-bottom: 25px; }
    .login-box input { width: 100%%; padding: 12px; margin: 8px 0; border: 1px solid #ddd;
                       border-radius: 6px; font-size: 1em; }
    .login-box button { width: 100%%; padding: 12px; background: #4fc3f7; color: #fff;
                        border: none; border-radius: 6px; font-size: 1em; cursor: pointer;
                        margin-top: 15px; }
    .login-box button:hover { background: #29b6f6; }
    .error { color: #e74c3c; text-align: center; margin-bottom: 15px; font-size: 0.9em; }
    .dash-header { background: #1a1a2e; color: #fff; padding: 20px 40px; }
    .dash-header h1 { font-size: 1.4em; }
    .dash-header span { color: #4fc3f7; }
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
    <a href="/" class="brand">NovaTech Solutions</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/services">Services</a>
    <a href="/contact">Contact</a>
</nav>
"""

FOOTER = """
<div class="footer">
    &copy; 2024 NovaTech Solutions, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy Policy</a> &bull; <a href="/terms">Terms of Service</a><br>
    Austin, TX &bull; San Francisco, CA &bull; New York, NY
</div>
"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>NovaTech Solutions</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>NovaTech Solutions</h1>
    <p>Enterprise software consulting &bull; Cloud architecture &bull; Digital transformation</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Custom Development</h2>
            <p>Full-stack engineering teams delivering production-grade applications.
            From microservices to monoliths, we build software that scales.</p>
        </div>
        <div class="card">
            <h2>Cloud Migration</h2>
            <p>Seamless migration strategies for AWS, Azure, and GCP. Reduce costs
            by 40%% while improving reliability and deployment velocity.</p>
        </div>
        <div class="card">
            <h2>DevOps &amp; SRE</h2>
            <p>CI/CD pipelines, infrastructure as code, and 24/7 monitoring.
            We keep your systems running so you can focus on your product.</p>
        </div>
    </div>
    <div class="card">
        <h2>Trusted by Industry Leaders</h2>
        <p>NovaTech has delivered over 200 projects for Fortune 500 clients across
        healthcare, fintech, and logistics. Our 98%% client retention rate speaks
        for itself.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - NovaTech Solutions</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>About NovaTech</h2>
        <p>Founded in 2016 by Elena Vasquez and James Chen, NovaTech Solutions began as a
        two-person consulting shop in Austin, Texas. Eight years later, we're a team of 85
        engineers, designers, and strategists serving clients across three continents.</p>
        <br>
        <p>Our philosophy is simple: build it right the first time. We invest in understanding
        your business before writing a single line of code. This approach has earned us
        partnerships with companies like MedCore Health Systems, Apex Financial Group, and
        TransGlobal Logistics.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>Elena Vasquez</strong>. CEO &amp; Co-Founder<br>
        <strong>James Chen</strong>. CTO &amp; Co-Founder<br>
        <strong>Devon Harris</strong>. VP of Engineering<br>
        <strong>Sarah Kim</strong>. Director of Client Services</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/services")
def services():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Services - NovaTech Solutions</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Our Services</h2>
        <ul style="line-height: 2; padding-left: 20px;">
            <li>Full-Stack Web Application Development</li>
            <li>Mobile Application Development (iOS &amp; Android)</li>
            <li>Cloud Architecture &amp; Migration (AWS, Azure, GCP)</li>
            <li>DevOps &amp; CI/CD Pipeline Engineering</li>
            <li>Data Engineering &amp; Analytics Platforms</li>
            <li>Security Assessment &amp; Compliance Consulting</li>
            <li>Legacy System Modernization</li>
            <li>Staff Augmentation &amp; Team Scaling</li>
        </ul>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/contact")
def contact():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Contact - NovaTech Solutions</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Get in Touch</h2>
        <p><strong>Headquarters:</strong> 401 Congress Ave, Suite 1200, Austin, TX 78701<br>
        <strong>Phone:</strong> (512) 555-0187<br>
        <strong>Email:</strong> info@novatech-solutions.com<br>
        <strong>Sales:</strong> sales@novatech-solutions.com</p>
        <br>
        <p><strong>San Francisco Office:</strong> 44 Montgomery St, Suite 3800, San Francisco, CA 94104<br>
        <strong>New York Office:</strong> 1 World Trade Center, Floor 72, New York, NY 10007</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Disallow: /staff-portal/
Disallow: /backup/
Disallow: /api/
Disallow: /internal/
""", 200, {"Content-Type": "text/plain"}


# ═══════════════════════════════════════════════════════════════════════
# Decoy endpoints (found by gobuster, not useful for the challenge)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/backup/")
def backup():
    return "403 Forbidden", 403

@app.route("/api/")
def api_root():
    return '{"error":"unauthorized","message":"API key required"}', 401, \
           {"Content-Type": "application/json"}

@app.route("/internal/")
def internal():
    return redirect("/")


# ═══════════════════════════════════════════════════════════════════════
# Staff Portal (hidden. must be discovered via directory enumeration)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/staff-portal/")
def staff_login():
    error_msg = ""
    if request.args.get("error"):
        error_msg = '<p class="error">Invalid username or password. Please try again.</p>'

    # The HTML comment below contains assessment token 1 (h1dd3n)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NovaTech Staff Portal</title>
    {STYLE}
</head>
<!-- NovaTech Staff Portal v2.1 | Build: h1dd3n-a7f2 | Deployed: 2024-09-15 staging-3 -->
<!-- TODO: Remove before production deployment. Devon -->
<body style="background: #1a1a2e;">
<div class="login-container">
    <div class="login-box">
        <h2>NovaTech Staff Portal</h2>
        {error_msg}
        <form method="POST" action="/staff-portal/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <p style="text-align: center; margin-top: 20px; font-size: 0.8em; color: #999;">
            Internal use only. Contact IT for access.
        </p>
    </div>
</div>
</body></html>"""


@app.route("/staff-portal/login", methods=["POST"])
def staff_do_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == "admin" and password == "NovaTech2024#":
        resp = make_response(redirect("/staff-portal/dashboard"))
        resp.set_cookie("staff_session", "admin_authenticated_v2")
        return resp

    return redirect("/staff-portal/?error=1")


@app.route("/staff-portal/dashboard")
def staff_dashboard():
    if request.cookies.get("staff_session") != "admin_authenticated_v2":
        return redirect("/staff-portal/")

    # Assessment token 2 (d3f4ult) is displayed as the auth token prefix
    # MySQL credentials are "accidentally" shown in the config panel
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Staff Dashboard - NovaTech</title>{STYLE}</head>
<body>
<div class="dash-header">
    <h1>NovaTech <span>Staff Dashboard</span></h1>
</div>
<div class="dash-body">
    <div class="card">
        <h2>System Status</h2>
        <table>
            <tr><th>Component</th><th>Status</th><th>Value</th></tr>
            <tr><td>Web Application</td><td><span class="badge badge-green">Online</span></td><td>v3.2.1</td></tr>
            <tr><td>Database</td><td><span class="badge badge-green">Connected</span></td><td>MySQL 8.0</td></tr>
            <tr><td>Auth Token Prefix</td><td><span class="badge badge-yellow">Active</span></td><td><code>d3f4ult</code></td></tr>
            <tr><td>Cache Layer</td><td><span class="badge badge-green">Online</span></td><td>Redis 7.2</td></tr>
            <tr><td>Background Workers</td><td><span class="badge badge-green">Running</span></td><td>4 active</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Quick Links</h2>
        <ul style="line-height: 2; padding-left: 20px;">
            <li>Employee Directory (SSO required)</li>
            <li>Project Management (Jira)</li>
            <li>Code Repository (GitHub Enterprise)</li>
            <li>Monitoring (Datadog)</li>
        </ul>
    </div>

    <div class="card">
        <h2>Application Configuration</h2>
        <p style="color: #888; font-size: 0.9em;">Current production environment settings:</p>
        <div class="config-block">APP_ENV=production
APP_VERSION=3.2.1
DB_HOST=novatech-db
DB_PORT=3306
DB_NAME=novatech
DB_USER=novatech_app
DB_PASS=Pr0d_DB_2024#
REDIS_HOST=localhost
REDIS_PORT=6379
SESSION_SECRET=a7f2c9e1b3d4...</div>
        <p style="color: #e74c3c; font-size: 0.8em; margin-top: 10px;">
            &#9888; This panel should not be exposed in production. See JIRA-4721.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
# Catch-all for common gobuster hits
# ═══════════════════════════════════════════════════════════════════════

@app.route("/admin")
@app.route("/admin/")
def admin_redirect():
    return redirect("/staff-portal/")

@app.route("/login")
@app.route("/login/")
def login_redirect():
    return redirect("/staff-portal/")

@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html><head><title>Privacy - NovaTech</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Privacy Policy</h2><p>NovaTech Solutions is committed to protecting your privacy.
This policy outlines how we collect, use, and safeguard your information.</p>
</div></div>{FOOTER}</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html><head><title>Terms - NovaTech</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Terms of Service</h2><p>By using NovaTech Solutions services, you agree to the
following terms and conditions.</p></div></div>{FOOTER}</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
