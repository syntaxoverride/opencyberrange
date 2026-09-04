"""
Nexus Dynamics. Enterprise SaaS Platform (Perimeter Server)

A deliberately vulnerable Flask application with command injection on /healthcheck.
The .env file in the same directory leaks SSH credentials for the core server.
"""

from flask import Flask, request
import subprocess

app = Flask(__name__)

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #e2e8f0; }
    .nav { background: #0b1120; padding: 15px 40px; display: flex; align-items: center;
           gap: 30px; border-bottom: 1px solid #1e293b; }
    .nav .brand { color: #38bdf8; font-weight: bold; font-size: 1.2em; margin-right: auto;
                  text-decoration: none; letter-spacing: 1px; }
    .nav a { color: #64748b; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #38bdf8; }
    .hero { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f2744 100%);
            padding: 80px 40px; text-align: center; border-bottom: 2px solid #38bdf8; }
    .hero h1 { color: #38bdf8; font-size: 2.8em; letter-spacing: 2px; margin-bottom: 15px; }
    .hero p { color: #94a3b8; font-size: 1.15em; max-width: 600px; margin: 0 auto; }
    .content { max-width: 960px; margin: 40px auto; padding: 0 20px; }
    .card { background: #1e293b; border-radius: 8px; padding: 30px; margin: 20px 0;
            border: 1px solid #334155; }
    .card h2 { color: #38bdf8; margin-bottom: 15px; }
    .card p { line-height: 1.7; color: #94a3b8; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .footer { text-align: center; padding: 30px; color: #475569; font-size: 0.8em;
              border-top: 1px solid #1e293b; margin-top: 60px; }
    .footer a { color: #38bdf8; text-decoration: none; }
    input[type=text] { width: 70%%; padding: 10px; background: #0f172a; border: 1px solid #334155;
                       color: #e2e8f0; border-radius: 4px; font-size: 1em; }
    button { padding: 10px 25px; background: #38bdf8; color: #0f172a; border: none;
             border-radius: 4px; font-size: 1em; cursor: pointer; margin-left: 10px;
             font-weight: bold; }
    button:hover { background: #0ea5e9; }
    pre { background: #0f172a; border: 1px solid #334155; padding: 15px; border-radius: 4px;
          overflow-x: auto; margin-top: 15px; color: #4ade80; font-size: 0.9em; }
    .note { color: #64748b; font-size: 0.85em; margin-top: 10px; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">NEXUS DYNAMICS</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/platform">Platform</a>
    <a href="/healthcheck">Health Check</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 Nexus Dynamics, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a> &bull;
    <a href="/status">System Status</a><br>
    Denver, CO &bull; Austin, TX &bull; Toronto, ON
</div>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Nexus Dynamics</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>NEXUS DYNAMICS</h1>
    <p>Enterprise SaaS Platform &bull; Workflow Automation &bull; Business Intelligence</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Workflow Engine</h2>
            <p>Automate complex business processes with our drag-and-drop workflow builder.
            Connect to 200+ enterprise integrations out of the box.</p>
        </div>
        <div class="card">
            <h2>Analytics Suite</h2>
            <p>Real-time dashboards, custom KPI tracking, and automated reporting.
            Turn your operational data into actionable intelligence.</p>
        </div>
        <div class="card">
            <h2>API Platform</h2>
            <p>RESTful APIs with comprehensive documentation. Build custom integrations
            or leverage our pre-built connectors for Salesforce, SAP, and more.</p>
        </div>
    </div>
    <div class="card">
        <h2>Trusted by Mid-Market Leaders</h2>
        <p>Over 450 companies rely on Nexus Dynamics to power their operations.
        From manufacturing to healthcare, our platform adapts to your industry's
        unique requirements. SOC 2 Type II certified.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - Nexus Dynamics</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>About Nexus Dynamics</h2>
        <p>Founded in 2019, Nexus Dynamics was born from a simple idea: mid-market
        companies deserve enterprise-grade tools without enterprise-grade complexity.
        Our founding team. veterans of Salesforce, ServiceNow, and Workday. built
        a platform that delivers powerful automation without the six-month implementation cycle.</p>
        <br>
        <p>Today we serve 450+ customers across manufacturing, healthcare, professional
        services, and logistics. Our Denver headquarters houses our engineering and product
        teams, with satellite offices in Austin and Toronto.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>Sarah Whitfield</strong>. CEO &amp; Co-Founder<br>
        <strong>Raj Patel</strong>. CTO &amp; Co-Founder<br>
        <strong>Marcus Hale</strong>. VP of Engineering<br>
        <strong>Emily Tran</strong>. VP of Customer Success</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/platform")
def platform():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Platform - Nexus Dynamics</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>The Nexus Platform</h2>
        <p>A unified platform for workflow automation, data integration, and business intelligence.
        Deploy on our cloud or in your own infrastructure.</p>
    </div>
    <div class="grid">
        <div class="card">
            <h2>Integrations</h2>
            <p>Salesforce, SAP, NetSuite, Workday, Slack, Jira, ServiceNow, HubSpot,
            and 190+ more. Connect your entire stack.</p>
        </div>
        <div class="card">
            <h2>Security</h2>
            <p>SOC 2 Type II certified. AES-256 encryption at rest, TLS 1.3 in transit.
            Role-based access control with SSO/SAML support.</p>
        </div>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/status")
def status():
    return f"""<!DOCTYPE html>
<html><head><title>Status - Nexus Dynamics</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>System Status</h2>
<p>All systems operational. Platform version 4.1.2.</p>
<p class="note">For detailed health checks, use the <a href="/healthcheck" style="color:#38bdf8;">Health Check</a> tool.</p>
</div></div>{FOOTER}</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
# Health check. VULNERABLE to command injection
# ═══════════════════════════════════════════════════════════════════════

@app.route("/healthcheck", methods=["GET", "POST"])
def healthcheck():
    if request.method == "GET":
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Health Check - Nexus Dynamics</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>System Health Check</h2>
        <p>Verify connectivity to internal and external services from the Nexus perimeter.</p>
        <form method="POST" style="margin-top:20px;">
            <input type="text" name="host" placeholder="Enter hostname or IP (e.g., 8.8.8.8)" required>
            <button type="submit">Check</button>
        </form>
        <p class="note">Sends a single ICMP echo request to the specified host.</p>
    </div>
</div>
{FOOTER}
</body></html>"""

    host = request.form.get("host", "")
    if not host:
        return "Missing host", 400

    # VULNERABLE: User input passed directly to shell command
    try:
        r = subprocess.run(
            f"ping -c 1 -W 2 {host}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=8
        )
        out = r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        out = "Request timed out."
    except Exception as e:
        out = f"Error: {str(e)}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Health Check Results - Nexus Dynamics</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Results for: {host}</h2>
        <pre>{out}</pre>
        <p style="margin-top:15px;"><a href="/healthcheck" style="color:#38bdf8;">Run another check</a></p>
    </div>
</div>
{FOOTER}
</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
