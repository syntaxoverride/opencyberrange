"""
Zenith Global Corp. Customer Tracking Portal

A deliberately vulnerable Flask API with an IDOR vulnerability.
Order #7 contains internal maintenance credentials (SSH creds for appserver).
The /api/config endpoint has broken access control exposing marker 1.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Order data. Order #7 is the IDOR target (internal credentials leak)
# ═══════════════════════════════════════════════════════════════════════

ORDERS = {
    1: {"id": 1, "customer": "Acme Corp", "status": "delivered", "items": 3,
        "tracking": "ZG-2024-00142", "origin": "Chicago, IL", "destination": "Tokyo, JP"},
    2: {"id": 2, "customer": "GlobalTech", "status": "in_transit", "items": 12,
        "tracking": "ZG-2024-00287", "origin": "Los Angeles, CA", "destination": "London, UK"},
    3: {"id": 3, "customer": "Pacific Trading", "status": "delivered", "items": 7,
        "tracking": "ZG-2024-00391", "origin": "New York, NY", "destination": "Sydney, AU"},
    4: {"id": 4, "customer": "Northern Logistics", "status": "processing", "items": 1,
        "tracking": "ZG-2024-00455", "origin": "Seattle, WA", "destination": "Hamburg, DE"},
    5: {"id": 5, "customer": "Summit Industries", "status": "delivered", "items": 22,
        "tracking": "ZG-2024-00510", "origin": "Dallas, TX", "destination": "Singapore, SG"},
    6: {"id": 6, "customer": "Ridgeline LLC", "status": "cancelled", "items": 4,
        "tracking": "ZG-2024-00603", "origin": "Miami, FL", "destination": "Dubai, AE"},
    7: {"id": 7, "customer": "INTERNAL", "status": "maintenance", "items": 0,
        "internal_notes": "App server maintenance credentials. appuser / Z3n1th_App_2024#. DO NOT EXPOSE TO CUSTOMERS"},
    8: {"id": 8, "customer": "Atlas Freight", "status": "delivered", "items": 9,
        "tracking": "ZG-2024-00718", "origin": "Boston, MA", "destination": "Mumbai, IN"},
}

# ═══════════════════════════════════════════════════════════════════════
# Shared HTML components
# ═══════════════════════════════════════════════════════════════════════

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Georgia', 'Times New Roman', serif; background: #0c1821; color: #ccd6f6; }
    .nav { background: #0a1628; padding: 15px 40px; display: flex; align-items: center;
           gap: 30px; border-bottom: 1px solid #1d2d44; }
    .nav .brand { color: #f0c040; font-weight: bold; font-size: 1.3em; letter-spacing: 2px;
                  margin-right: auto; text-decoration: none; }
    .nav a { color: #8892b0; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #f0c040; }
    .hero { background: linear-gradient(135deg, #0c1821 0%, #1b2838 50%, #162447 100%);
            padding: 80px 40px; text-align: center; border-bottom: 2px solid #f0c040; }
    .hero h1 { color: #f0c040; font-size: 3em; letter-spacing: 4px; margin-bottom: 15px; }
    .hero p { color: #8892b0; font-size: 1.15em; max-width: 600px; margin: 0 auto; }
    .content { max-width: 960px; margin: 40px auto; padding: 0 20px; }
    .card { background: #112240; border-radius: 8px; padding: 30px; margin: 20px 0;
            border: 1px solid #1d2d44; }
    .card h2 { color: #f0c040; margin-bottom: 15px; }
    .card p { line-height: 1.7; color: #a8b2d1; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .stat { text-align: center; padding: 25px; }
    .stat .number { color: #f0c040; font-size: 2.5em; font-weight: bold; }
    .stat .label { color: #8892b0; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px;
                   margin-top: 5px; }
    .footer { text-align: center; padding: 30px; color: #495670; font-size: 0.8em;
              border-top: 1px solid #1d2d44; margin-top: 60px; }
    .footer a { color: #f0c040; text-decoration: none; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th { background: #1d2d44; padding: 12px; text-align: left; font-size: 0.8em;
         color: #8892b0; text-transform: uppercase; letter-spacing: 1px; }
    td { padding: 12px; border-bottom: 1px solid #1d2d44; color: #a8b2d1; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.75em;
             font-weight: bold; text-transform: uppercase; }
    .badge-delivered { background: #1a3a2a; color: #4ade80; }
    .badge-transit { background: #1a2a3a; color: #60a5fa; }
    .badge-processing { background: #3a3a1a; color: #facc15; }
    .badge-cancelled { background: #3a1a1a; color: #f87171; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">ZENITH GLOBAL</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/tracking">Tracking</a>
    <a href="/api/docs">API</a>
    <a href="/contact">Contact</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 Zenith Global Corp. All rights reserved.<br>
    <a href="/privacy">Privacy</a> &bull; <a href="/terms">Terms</a> &bull;
    <a href="/api/docs">Developer API</a><br>
    Chicago, IL &bull; London, UK &bull; Tokyo, JP &bull; Sydney, AU
</div>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Zenith Global Corp</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>ZENITH GLOBAL</h1>
    <p>Global Logistics &bull; Supply Chain Management &bull; Freight Solutions</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card stat">
            <div class="number">47</div>
            <div class="label">Countries Served</div>
        </div>
        <div class="card stat">
            <div class="number">12K+</div>
            <div class="label">Shipments Monthly</div>
        </div>
        <div class="card stat">
            <div class="number">99.4%%</div>
            <div class="label">On-Time Delivery</div>
        </div>
    </div>
    <div class="grid">
        <div class="card">
            <h2>Ocean Freight</h2>
            <p>Full container load (FCL) and less-than-container load (LCL) services
            across all major trade lanes. Real-time container tracking and port-to-door delivery.</p>
        </div>
        <div class="card">
            <h2>Air Cargo</h2>
            <p>Time-critical shipments handled with care. Express, standard, and charter
            options with guaranteed delivery windows and temperature-controlled capacity.</p>
        </div>
        <div class="card">
            <h2>Supply Chain</h2>
            <p>End-to-end supply chain visibility. Warehouse management, customs brokerage,
            and last-mile delivery integrated into a single platform.</p>
        </div>
    </div>
    <div class="card">
        <h2>Trusted by Global Enterprises</h2>
        <p>For over 25 years, Zenith Global has connected manufacturers, retailers, and
        distributors across six continents. Our proprietary tracking platform processes
        over 12,000 shipments monthly with a 99.4%% on-time delivery rate.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - Zenith Global</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Our Story</h2>
        <p>Founded in 1998 by Marcus Hale and Lin Wei, Zenith Global began as a small
        freight brokerage on Chicago's South Side. Today, we are a multinational logistics
        company with operations in 47 countries and a team of over 2,800 professionals.</p>
        <br>
        <p>Our philosophy is built on three pillars: reliability, visibility, and partnership.
        We don't just move cargo. we architect supply chains that give our clients a
        competitive advantage in the global marketplace.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>Marcus Hale</strong>. CEO &amp; Co-Founder<br>
        <strong>Lin Wei</strong>. COO &amp; Co-Founder<br>
        <strong>Diane Holloway</strong>. Chief Information Security Officer<br>
        <strong>James Okafor</strong>. VP, Global Operations<br>
        <strong>Rachel Nguyen</strong>. VP, Technology &amp; Engineering</p>
    </div>
    <div class="card">
        <h2>Global Presence</h2>
        <p>Headquarters in Chicago with regional hubs in London, Tokyo, Sydney, Dubai,
        and S&atilde;o Paulo. Our network covers 47 countries with over 200 partner
        facilities worldwide.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/tracking")
def tracking():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Tracking - Zenith Global</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Shipment Tracking</h2>
        <p>Track your shipment using the Zenith Global Tracking API. Enter your
        tracking number or use our REST API for automated integration.</p>
        <br>
        <p style="color:#8892b0;">API Endpoint: <code style="color:#f0c040;">/api/orders</code></p>
        <p style="color:#8892b0;">Documentation: <code style="color:#f0c040;"><a href="/api/docs" style="color:#f0c040;">/api/docs</a></code></p>
    </div>
    <div class="card">
        <h2>Recent Shipments</h2>
        <table>
            <tr><th>Tracking ID</th><th>Customer</th><th>Route</th><th>Status</th></tr>
            <tr><td>ZG-2024-00142</td><td>Acme Corp</td><td>Chicago &rarr; Tokyo</td>
                <td><span class="badge badge-delivered">Delivered</span></td></tr>
            <tr><td>ZG-2024-00287</td><td>GlobalTech</td><td>Los Angeles &rarr; London</td>
                <td><span class="badge badge-transit">In Transit</span></td></tr>
            <tr><td>ZG-2024-00391</td><td>Pacific Trading</td><td>New York &rarr; Sydney</td>
                <td><span class="badge badge-delivered">Delivered</span></td></tr>
            <tr><td>ZG-2024-00455</td><td>Northern Logistics</td><td>Seattle &rarr; Hamburg</td>
                <td><span class="badge badge-processing">Processing</span></td></tr>
        </table>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/contact")
def contact():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Contact - Zenith Global</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Contact Us</h2>
        <p><strong>Global Headquarters:</strong><br>
        233 S Wacker Dr, Suite 4700, Chicago, IL 60606<br>
        Phone: (312) 555-0198<br>
        Email: info@zenith-global.com</p>
        <br>
        <p><strong>Sales &amp; Partnerships:</strong> sales@zenith-global.com<br>
        <strong>Technical Support:</strong> api-support@zenith-global.com<br>
        <strong>Media Inquiries:</strong> press@zenith-global.com</p>
    </div>
    <div class="grid">
        <div class="card">
            <h2>London Office</h2>
            <p>20 Fenchurch St, Floor 18<br>London, EC3M 3BY, UK<br>+44 20 7946 0958</p>
        </div>
        <div class="card">
            <h2>Tokyo Office</h2>
            <p>Marunouchi Park Building, 14F<br>Chiyoda-ku, Tokyo 100-6914<br>+81 3 6270 2800</p>
        </div>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html><head><title>Privacy - Zenith Global</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Privacy Policy</h2><p>Zenith Global Corp is committed to protecting your data.
We collect only the information necessary to provide our logistics and tracking services.
For questions about your data, contact privacy@zenith-global.com.</p>
</div></div>{FOOTER}</body></html>"""


@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html><head><title>Terms - Zenith Global</title>{STYLE}</head><body>
{NAV}<div class="content" style="margin-top:40px;"><div class="card">
<h2>Terms of Service</h2><p>Use of the Zenith Global tracking platform and API is subject
to these terms. By accessing our services, you agree to comply with all applicable
regulations governing international freight and customs.</p>
</div></div>{FOOTER}</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
# API endpoints
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/docs")
def docs():
    return jsonify({
        "api": "Zenith Global Tracking API",
        "version": "2.1",
        "base_url": "/api",
        "endpoints": {
            "GET /api/orders": "List all customer orders",
            "GET /api/orders/<id>": "Get order details by ID"
        },
        "authentication": "API key required for production use. Contact api-support@zenith-global.com.",
        "rate_limit": "60 requests/minute",
        "contact": "api-support@zenith-global.com"
    })


@app.route("/api/orders")
def list_orders():
    return jsonify({"orders": [
        {"id": o["id"], "customer": o["customer"], "status": o["status"]}
        for o in ORDERS.values() if o["customer"] != "INTERNAL"
    ]})


@app.route("/api/orders/<int:oid>")
def get_order(oid):
    if oid in ORDERS:
        return jsonify(ORDERS[oid])
    return jsonify({"error": "not found"}), 404


# Broken access control. exposes marker 1 without authentication
@app.route("/api/config")
def config():
    return jsonify({
        "env": "production",
        "marker": "z3n1th",
        "version": "2.1.4",
        "warning": "This endpoint should require authentication"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
