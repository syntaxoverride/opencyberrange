"""
Atlas Distribution - Corpus Christi Branch Intranet Portal

Deliberately vulnerable Flask app for the Week 15 final exam practice.
Multiple legitimate-looking pages plus a hidden staff portal at /staff-portal/
that accepts a SQL injection authentication bypass.
"""

import sqlite3
from flask import Flask, request, redirect, make_response

app = Flask(__name__)

WEB_TOKEN = "token=3xc3l"


def get_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE staff (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    cur.execute("INSERT INTO staff VALUES (1, 'admin', 'M3l1ss4_2024', 'administrator')")
    cur.execute("INSERT INTO staff VALUES (2, 'bholm', 'BrianH_2025#', 'staff')")
    cur.execute("INSERT INTO staff VALUES (3, 'kvogel', 'KarenV_2024#', 'manager')")
    conn.commit()
    return conn


# Reused style and chrome
STYLE = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f6f8; color: #2c3e50; }
    .nav { background: #1d3557; padding: 14px 40px; display: flex; align-items: center; gap: 28px; }
    .nav a { color: #a8c0d6; text-decoration: none; font-size: 0.95em; }
    .nav a:hover { color: #fff; }
    .nav .brand { color: #f1c40f; font-weight: 700; font-size: 1.15em; margin-right: auto; letter-spacing: 0.5px; }
    .hero { background: linear-gradient(135deg, #1d3557 0%, #285186 60%, #4072a8 100%);
            padding: 80px 40px; text-align: center; color: #fff; }
    .hero h1 { font-size: 2.6em; margin-bottom: 12px; }
    .hero p { font-size: 1.1em; color: #cfe0f0; max-width: 640px; margin: 0 auto; }
    .content { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 8px; padding: 28px; margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .card h2 { color: #1d3557; margin-bottom: 14px; }
    .card h3 { color: #2c4a73; margin-bottom: 10px; margin-top: 16px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
    .footer { text-align: center; padding: 30px; color: #7b8a99; font-size: 0.85em;
              border-top: 1px solid #dde3ea; margin-top: 50px; background: #fff; }
    .footer a { color: #1d3557; text-decoration: none; }
    .login-container { max-width: 420px; margin: 80px auto; }
    .login-box { background: #fff; border-radius: 8px; padding: 36px;
                 box-shadow: 0 4px 18px rgba(0,0,0,0.12); }
    .login-box h2 { text-align: center; color: #1d3557; margin-bottom: 22px; }
    .login-box input { width: 100%%; padding: 11px; margin: 7px 0; border: 1px solid #cfd8e0;
                       border-radius: 5px; font-size: 0.95em; }
    .login-box button { width: 100%%; padding: 11px; background: #1d3557; color: #fff;
                        border: none; border-radius: 5px; font-size: 1em; cursor: pointer;
                        margin-top: 14px; font-weight: 600; }
    .login-box button:hover { background: #2c4a73; }
    .error { color: #c0392b; text-align: center; margin-bottom: 12px; font-size: 0.88em; }
    .dash-header { background: #1d3557; color: #fff; padding: 22px 40px; }
    .dash-header h1 { font-size: 1.4em; }
    .dash-header span { color: #f1c40f; }
    .dash-body { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
    table { width: 100%%; border-collapse: collapse; }
    table th { background: #f1f4f7; padding: 12px; text-align: left; font-size: 0.82em;
               color: #5a6a7d; text-transform: uppercase; letter-spacing: 0.5px; }
    table td { padding: 12px; border-bottom: 1px solid #ecf0f4; }
    .badge { display: inline-block; padding: 3px 11px; border-radius: 12px; font-size: 0.78em; font-weight: 600; }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-blue { background: #d1ecf1; color: #0c5460; }
    .config-block { background: #f1f4f7; border: 1px solid #cfd8e0; border-radius: 5px;
                    padding: 14px; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.85em; margin: 12px 0;
                    white-space: pre-wrap; color: #2c3e50; }
    .news-item { padding: 18px; border-bottom: 1px solid #ecf0f4; }
    .news-item:last-child { border-bottom: none; }
    .news-item h3 { color: #1d3557; }
    .news-item .meta { color: #7b8a99; font-size: 0.85em; margin: 6px 0 12px; }
    .news-item a { color: #1d3557; text-decoration: none; font-weight: 600; }
    .job-item { padding: 14px 0; border-bottom: 1px solid #ecf0f4; }
    .job-item:last-child { border-bottom: none; }
    .job-item .title { font-weight: 600; color: #1d3557; }
    .job-item .loc { color: #7b8a99; font-size: 0.88em; }
</style>
"""

NAV = """
<nav class="nav">
    <a href="/" class="brand">Atlas Distribution</a>
    <a href="/">Home</a>
    <a href="/about">About</a>
    <a href="/services">Services</a>
    <a href="/locations">Locations</a>
    <a href="/news/">News</a>
    <a href="/careers/">Careers</a>
    <a href="/contact">Contact</a>
</nav>
"""

FOOTER = """
<div class="footer">
    &copy; 2025 Atlas Distribution, Inc. All rights reserved.<br>
    <a href="/privacy">Privacy Policy</a> &bull; <a href="/terms">Terms of Service</a> &bull; <a href="/login">Employee Login</a><br>
    Atlanta, GA &bull; Dallas, TX &bull; Phoenix, AZ &bull; Corpus Christi, TX
</div>
"""


def page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title}</title>{STYLE}</head>
<body>
{NAV}
{body}
{FOOTER}
</body></html>"""


# Public pages

@app.route("/")
def index():
    return page("Atlas Distribution", """
<div class="hero">
    <h1>Atlas Distribution</h1>
    <p>Regional logistics, last-mile delivery, and bonded warehousing across the Gulf Coast.</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Regional Logistics</h2>
            <p>Twelve regional branches serving the Gulf Coast and southwest United States. Daily dispatch volume exceeds 14,000 packages.</p>
        </div>
        <div class="card">
            <h2>Bonded Warehousing</h2>
            <p>U.S. Customs bonded storage at our Corpus Christi and Houston yards for international transit shipments.</p>
        </div>
        <div class="card">
            <h2>Last-Mile Delivery</h2>
            <p>Dedicated last-mile fleets in fourteen metro areas. Same-day and next-day windows available.</p>
        </div>
    </div>
    <div class="card">
        <h2>Branch Spotlight: Corpus Christi</h2>
        <p>The Corpus Christi branch has served South Texas customers for twenty-three years. Our forty-person team handles dispatch, receiving, and customer support for a region covering Nueces, San Patricio, Aransas, and Kleberg counties.</p>
    </div>
</div>
""")


@app.route("/about")
def about():
    return page("About - Atlas Distribution", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>About Atlas Distribution</h2>
        <p>Atlas Distribution was founded in 1986 by William Ashworth as a single-truck delivery service in Atlanta, Georgia. Over four decades, the company has grown into a regional logistics firm with twelve branches, four hundred employees, and an annual delivery volume north of five million packages.</p>
        <br>
        <p>Our mission is simple: get freight where it needs to go, safely, on time, and at a price that is fair to both shipper and recipient. We invest in our drivers, our facilities, and our technology so the companies that depend on us never have to think twice about whether their shipment will arrive.</p>
    </div>
    <div class="card">
        <h2>Leadership</h2>
        <p><strong>James Ashworth</strong> &middot; Chief Executive Officer<br>
        <strong>Karen Vogel</strong> &middot; Director of Corporate Security<br>
        <strong>Dana Reyes</strong> &middot; Vice President of Operations<br>
        <strong>Tomas Fischer</strong> &middot; Chief Financial Officer<br>
        <strong>Renata Ortiz</strong> &middot; General Counsel</p>
    </div>
    <div class="card">
        <h2>By the Numbers</h2>
        <p>12 branch locations &bull; 400+ employees &bull; 220 trucks &bull; 5.2M packages delivered in 2024 &bull; 99.4 percent on-time delivery rate</p>
    </div>
</div>
""")


@app.route("/services")
def services():
    return page("Services - Atlas Distribution", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Our Services</h2>
        <ul style="line-height: 1.9; padding-left: 22px;">
            <li><strong>Regional LTL Freight</strong> &mdash; less-than-truckload service across the Gulf Coast and southwest U.S.</li>
            <li><strong>Last-Mile Delivery</strong> &mdash; dedicated fleets in fourteen metro markets</li>
            <li><strong>Bonded Warehousing</strong> &mdash; U.S. Customs bonded storage at two yards</li>
            <li><strong>Cross-Dock Operations</strong> &mdash; same-day staging and reload at all twelve branches</li>
            <li><strong>Returns Management</strong> &mdash; reverse logistics for e-commerce shippers</li>
            <li><strong>Hazmat Transport</strong> &mdash; certified drivers and equipment for placarded loads</li>
            <li><strong>White-Glove Delivery</strong> &mdash; specialized handling for high-value freight</li>
        </ul>
    </div>
    <div class="card">
        <h2>Branch Service Areas</h2>
        <p>Our Corpus Christi branch directly serves Nueces, San Patricio, Aransas, Kleberg, and Bee counties. Pickups and deliveries to Brooks, Live Oak, and Kenedy counties are available with twenty-four hour notice.</p>
    </div>
</div>
""")


@app.route("/locations")
def locations():
    return page("Locations - Atlas Distribution", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Branch Locations</h2>
        <table>
            <tr><th>Branch</th><th>City</th><th>State</th><th>Phone</th></tr>
            <tr><td>Corporate HQ</td><td>Atlanta</td><td>GA</td><td>(404) 555-0100</td></tr>
            <tr><td>Dallas</td><td>Dallas</td><td>TX</td><td>(214) 555-0200</td></tr>
            <tr><td>Houston</td><td>Houston</td><td>TX</td><td>(713) 555-0300</td></tr>
            <tr><td>San Antonio</td><td>San Antonio</td><td>TX</td><td>(210) 555-0400</td></tr>
            <tr><td><strong>Corpus Christi</strong></td><td><strong>Corpus Christi</strong></td><td><strong>TX</strong></td><td><strong>(361) 555-0500</strong></td></tr>
            <tr><td>El Paso</td><td>El Paso</td><td>TX</td><td>(915) 555-0600</td></tr>
            <tr><td>Phoenix</td><td>Phoenix</td><td>AZ</td><td>(602) 555-0700</td></tr>
            <tr><td>Tucson</td><td>Tucson</td><td>AZ</td><td>(520) 555-0800</td></tr>
            <tr><td>Albuquerque</td><td>Albuquerque</td><td>NM</td><td>(505) 555-0900</td></tr>
            <tr><td>New Orleans</td><td>New Orleans</td><td>LA</td><td>(504) 555-1000</td></tr>
            <tr><td>Mobile</td><td>Mobile</td><td>AL</td><td>(251) 555-1100</td></tr>
            <tr><td>Jacksonville</td><td>Jacksonville</td><td>FL</td><td>(904) 555-1200</td></tr>
        </table>
    </div>
</div>
""")


# News pages (red herrings)

@app.route("/news/")
def news_index():
    return page("News - Atlas Distribution", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Branch News and Announcements</h2>
        <div class="news-item">
            <h3><a href="/news/2025-q3-shipping-volume/">Q3 2025 Shipping Volume Up 11 Percent Year-Over-Year</a></h3>
            <div class="meta">October 14, 2025 &bull; Operations</div>
            <p>Atlas Distribution closed the third quarter of 2025 with shipping volume up 11.2 percent compared to the same period in 2024. The Corpus Christi branch led the network in growth at 18 percent...</p>
        </div>
        <div class="news-item">
            <h3><a href="/news/2025-driver-safety-program/">New Driver Safety Program Launches Across All Branches</a></h3>
            <div class="meta">August 28, 2025 &bull; Safety</div>
            <p>Atlas has rolled out a refreshed driver safety program across all twelve branches. The program includes monthly defensive driving refreshers, telematics-driven coaching, and a quarterly safety bonus...</p>
        </div>
        <div class="news-item">
            <h3><a href="/news/2024-warehouse-expansion/">Corpus Christi Warehouse Expansion Completed</a></h3>
            <div class="meta">November 2, 2024 &bull; Facilities</div>
            <p>The Corpus Christi branch completed a 12,000 square foot warehouse expansion, bringing total bonded storage capacity to 38,000 square feet. The expansion supports growing demand from regional...</p>
        </div>
        <div class="news-item">
            <h3><a href="/news/2024-fleet-electrification/">Fleet Electrification Pilot in Phoenix and Tucson</a></h3>
            <div class="meta">May 18, 2024 &bull; Sustainability</div>
            <p>Atlas Distribution has placed an order for fourteen electric last-mile delivery vehicles to be deployed in Phoenix and Tucson. The pilot is part of a broader sustainability initiative...</p>
        </div>
    </div>
</div>
""")


@app.route("/news/2025-q3-shipping-volume/")
def news_q3():
    return page("Q3 2025 Shipping Volume - Atlas", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Q3 2025 Shipping Volume Up 11 Percent Year-Over-Year</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">October 14, 2025 &bull; Operations</div>
        <p>Atlas Distribution closed the third quarter of 2025 with shipping volume up 11.2 percent compared to the same period in 2024. The Corpus Christi branch led the network in growth at 18 percent, driven by new contract wins with three regional retailers and expanded last-mile coverage in Aransas and Kleberg counties.</p>
        <br>
        <p>Total package volume across the network reached 1.4 million for the quarter. On-time delivery held at 99.3 percent, slightly below the 2024 high of 99.5 percent. Operations Director Dana Reyes attributed the small dip to two named tropical systems that disrupted Gulf Coast routing in early September.</p>
        <br>
        <p>Looking ahead to the holiday peak, Atlas plans to add forty seasonal drivers across the southern branches and extend Saturday dispatch hours through the end of December.</p>
    </div>
</div>
""")


@app.route("/news/2025-driver-safety-program/")
def news_safety():
    return page("Driver Safety Program - Atlas", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>New Driver Safety Program Launches Across All Branches</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">August 28, 2025 &bull; Safety</div>
        <p>Atlas has rolled out a refreshed driver safety program across all twelve branches. The program includes monthly defensive driving refreshers, telematics-driven coaching, and a quarterly safety bonus for drivers who meet criteria across hard-braking, lane discipline, and on-time performance.</p>
        <br>
        <p>The launch follows a year-long pilot at the Dallas and Phoenix branches that produced a 22 percent reduction in preventable incidents. Safety Director Mike Whitley said the program will be revised quarterly based on telematics data and driver feedback.</p>
    </div>
</div>
""")


@app.route("/news/2024-warehouse-expansion/")
def news_warehouse():
    return page("Warehouse Expansion - Atlas", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Corpus Christi Warehouse Expansion Completed</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">November 2, 2024 &bull; Facilities</div>
        <p>The Corpus Christi branch completed a 12,000 square foot warehouse expansion, bringing total bonded storage capacity to 38,000 square feet. The expansion supports growing demand from regional importers and short-haul transit shippers staging freight at the Port of Corpus Christi.</p>
        <br>
        <p>The new floor includes climate-controlled racking for sensitive cargo and an additional dock door for tractor-trailer cross-docking. Construction was completed under budget and three weeks ahead of schedule.</p>
    </div>
</div>
""")


@app.route("/news/2024-fleet-electrification/")
def news_fleet():
    return page("Fleet Electrification - Atlas", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Fleet Electrification Pilot in Phoenix and Tucson</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">May 18, 2024 &bull; Sustainability</div>
        <p>Atlas Distribution has placed an order for fourteen electric last-mile delivery vehicles to be deployed in Phoenix and Tucson. The pilot is part of a broader sustainability initiative to reduce diesel consumption across the fleet by 15 percent over the next five years.</p>
        <br>
        <p>Charging infrastructure at both branches is scheduled for installation in Q4 2024, with the first electric vehicles entering service in early 2025.</p>
    </div>
</div>
""")


# Careers (red herring)

@app.route("/careers/")
def careers():
    return page("Careers - Atlas Distribution", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Open Positions</h2>
        <p>Atlas Distribution is hiring across the network. Click any role to view a full description and apply.</p>
        <br>
        <div class="job-item">
            <div class="title">CDL-A Driver - Day Shift</div>
            <div class="loc">Corpus Christi, TX &bull; Full-time &bull; Posted 2 days ago</div>
        </div>
        <div class="job-item">
            <div class="title">Dispatch Coordinator</div>
            <div class="loc">Houston, TX &bull; Full-time &bull; Posted 5 days ago</div>
        </div>
        <div class="job-item">
            <div class="title">Warehouse Associate (Receiving)</div>
            <div class="loc">Corpus Christi, TX &bull; Full-time &bull; Posted 6 days ago</div>
        </div>
        <div class="job-item">
            <div class="title">Last-Mile Driver - Box Truck</div>
            <div class="loc">Phoenix, AZ &bull; Full-time &bull; Posted 1 week ago</div>
        </div>
        <div class="job-item">
            <div class="title">Branch IT Administrator</div>
            <div class="loc">Corpus Christi, TX &bull; Full-time &bull; Posted 4 weeks ago &bull; Urgent</div>
        </div>
        <div class="job-item">
            <div class="title">Customer Support Representative</div>
            <div class="loc">Atlanta, GA &bull; Full-time &bull; Posted 2 weeks ago</div>
        </div>
    </div>
</div>
""")


@app.route("/contact")
def contact():
    return page("Contact - Atlas Distribution", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Get in Touch</h2>
        <p><strong>Corporate Headquarters:</strong> 1240 Peachtree Industrial Pkwy, Atlanta, GA 30341<br>
        <strong>Phone:</strong> (404) 555-0100<br>
        <strong>Email:</strong> contact@atlasdistribution.com<br>
        <strong>Customer Support:</strong> (404) 555-0150</p>
        <br>
        <p><strong>Corpus Christi Branch:</strong> 4400 Old Brownsville Rd, Corpus Christi, TX 78405<br>
        <strong>Branch Phone:</strong> (361) 555-0500<br>
        <strong>Dispatch Line:</strong> (361) 555-0501</p>
    </div>
</div>
""")


@app.route("/privacy")
def privacy():
    return page("Privacy - Atlas Distribution", """
<div class="content" style="margin-top:40px;"><div class="card">
<h2>Privacy Policy</h2>
<p>Atlas Distribution collects and processes personal data in accordance with applicable U.S. federal and state privacy laws. This policy outlines what data we collect, how we use it, and how we protect it.</p>
<br>
<p>We collect contact information you provide when scheduling a shipment, employment information from job applicants, and operational data from our drivers and dispatch systems. We do not sell personal data to third parties. Operational data is retained for seven years to comply with U.S. Department of Transportation rules.</p>
</div></div>
""")


@app.route("/terms")
def terms():
    return page("Terms - Atlas Distribution", """
<div class="content" style="margin-top:40px;"><div class="card">
<h2>Terms of Service</h2>
<p>Use of Atlas Distribution services is governed by the master service agreement signed between Atlas and the shipper. The terms below apply to general use of this website. Use of any branch portal beyond the marketing pages is restricted to authorized employees and contractors.</p>
</div></div>
""")


# Robots.txt - the discovery hint for the staff portal

@app.route("/robots.txt")
def robots():
    return """User-agent: *
Disallow: /staff-portal/
Disallow: /api/
Disallow: /legacy/
""", 200, {"Content-Type": "text/plain"}


# Decoy / red herring routes

@app.route("/login")
def login_decoy():
    return page("Employee Login - Atlas", """
<div class="content" style="margin-top:40px;"><div class="card">
<h2>Employee Login</h2>
<p>This page is no longer the active employee login. The branch staff portal has been moved. If you cannot reach the new portal, contact corporate IT.</p>
<br>
<p style="color:#7b8a99; font-size:0.85em;">Note from IT: a redirect for old bookmarks will be added in a future maintenance window.</p>
</div></div>
""")


@app.route("/api/")
def api_root():
    return '{"error":"unauthorized","message":"API access requires a valid bearer token. Contact corporate IT."}', 401, {"Content-Type": "application/json"}


@app.route("/api/v1/")
def api_v1():
    return '{"error":"deprecated","message":"v1 was retired in 2024. Migrate to v2."}', 410, {"Content-Type": "application/json"}


@app.route("/api/v2/health")
def api_v2_health():
    return '{"status":"ok","service":"branch-portal","version":"2.4.1"}', 200, {"Content-Type": "application/json"}


@app.route("/legacy/")
def legacy():
    return "404 Not Found", 404


@app.route("/admin")
@app.route("/admin/")
def admin_redirect():
    return redirect("/staff-portal/")


# Staff Portal: the actual vulnerable target

@app.route("/staff-portal/")
def staff_portal_login():
    error_msg = ""
    if request.args.get("error"):
        error_msg = '<p class="error">Invalid username or password.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Atlas Staff Portal</title>{STYLE}</head>
<body style="background:#1d3557;">
<div class="login-container">
    <div class="login-box">
        <h2>Atlas Staff Portal</h2>
        {error_msg}
        <form method="POST" action="/staff-portal/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <p style="text-align:center; margin-top:18px; font-size:0.78em; color:#999;">
            Branch staff only. All sessions are logged.
        </p>
    </div>
</div>
</body></html>"""


def _try_sqli_login(username, password):
    # VULNERABLE: SQL query built with string formatting against in-memory
    # sqlite. To make the form accept SQLi payloads written for any common
    # backend dialect, retry with MySQL-style # comments rewritten to the
    # ANSI -- form when the first attempt fails.
    payloads = [(username, password)]
    if "#" in username or "#" in password:
        payloads.append((username.replace("#", "--"), password.replace("#", "--")))
    for u, p in payloads:
        query = "SELECT id, username, role FROM staff WHERE username='%s' AND password='%s'" % (u, p)
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(query)
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return row
        except Exception:
            continue
    return None


@app.route("/staff-portal/login", methods=["POST"])
def staff_portal_do_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    row = _try_sqli_login(username, password)
    if row:
        resp = make_response(redirect("/staff-portal/dashboard"))
        resp.set_cookie("atlas_session", "authenticated_staff_v2")
        return resp
    return redirect("/staff-portal/?error=1")


@app.route("/staff-portal/dashboard")
def staff_portal_dashboard():
    if request.cookies.get("atlas_session") != "authenticated_staff_v2":
        return redirect("/staff-portal/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Staff Dashboard - Atlas</title>{STYLE}</head>
<body>
<div class="dash-header">
    <h1>Atlas <span>Staff Dashboard</span></h1>
</div>
<div class="dash-body">
    <div class="card">
        <h2>System Status</h2>
        <table>
            <tr><th>Component</th><th>Status</th><th>Detail</th></tr>
            <tr><td>Branch Portal</td><td><span class="badge badge-green">Online</span></td><td>v2.4.1</td></tr>
            <tr><td>Dispatch Backups</td><td><span class="badge badge-green">Last run 02:15</span></td><td>17,520 files</td></tr>
            <tr><td>Asset Token</td><td><span class="badge badge-yellow">Active</span></td><td><code>{WEB_TOKEN}</code></td></tr>
            <tr><td>Help Desk Liaison</td><td><span class="badge badge-blue">Vacant</span></td><td>Pending hire</td></tr>
        </table>
    </div>
    <div class="card">
        <h2>Open Tickets</h2>
        <table>
            <tr><th>ID</th><th>Subject</th><th>Status</th><th>Owner</th></tr>
            <tr><td>CCX-1148</td><td>Receiving floor scanner intermittent</td><td><span class="badge badge-yellow">Open</span></td><td>H. Diaz</td></tr>
            <tr><td>CCX-1145</td><td>Dispatch monitor flicker</td><td><span class="badge badge-blue">Investigating</span></td><td>(unassigned)</td></tr>
            <tr><td>CCX-1140</td><td>VPN reconnect required after timeout</td><td><span class="badge badge-green">Resolved</span></td><td>B. Holm</td></tr>
            <tr><td>CCX-1133</td><td>Printer driver mismatch on dispatch desk</td><td><span class="badge badge-green">Resolved</span></td><td>B. Holm</td></tr>
        </table>
    </div>
    <div class="card">
        <h2>Application Configuration</h2>
        <p style="color:#7b8a99; font-size:0.9em;">Read-only view of the running configuration.</p>
        <div class="config-block">APP_ENV=production
APP_VERSION=2.4.1
APP_BRANCH=corpus-christi
DB_DRIVER=sqlite
DB_PATH=/var/lib/atlas/portal.db
SMB_HOST=atlas-ccx-fs01
SMB_BACKUP_USER=dispatch_svc
LOG_LEVEL=info</div>
        <p style="color:#c0392b; font-size:0.8em; margin-top:10px;">
            &#9888; Configuration view should be restricted to administrators. See ticket CCX-1098.
        </p>
    </div>
</div>
{FOOTER}
</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
