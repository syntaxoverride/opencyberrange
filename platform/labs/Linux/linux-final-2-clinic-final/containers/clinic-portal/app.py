"""
Pinecrest Family Practice - Internal Staff Portal

Deliberately vulnerable Flask app for the Week 16B final exam.
Multiple legitimate-looking pages plus a hidden staff portal at /staff/
that accepts a SQL injection authentication bypass.

Same skill chain as the Atlas practice lab; different scenario, paths,
content, and flag values.
"""

import sqlite3
from flask import Flask, request, redirect, make_response

app = Flask(__name__)

WEB_TOKEN = "Token 3 = 0wn3d"


def get_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE staff (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    cur.execute("INSERT INTO staff VALUES (1, 'admin', 'P1n3cr3stAdm2024', 'administrator')")
    cur.execute("INSERT INTO staff VALUES (2, 'rcoombs', 'StillwaterIT_2024', 'contractor')")
    cur.execute("INSERT INTO staff VALUES (3, 'rpatel', 'ReneeP_2024#', 'manager')")
    cur.execute("INSERT INTO staff VALUES (4, 'mlinton', 'MLinton#2025', 'staff')")
    conn.commit()
    return conn


STYLE = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f7f5; color: #2c3e2c; }
    .nav { background: #2d5a3d; padding: 14px 40px; display: flex; align-items: center; gap: 28px; }
    .nav a { color: #c8dac9; text-decoration: none; font-size: 0.95em; }
    .nav a:hover { color: #fff; }
    .nav .brand { color: #f4d35e; font-weight: 700; font-size: 1.18em; margin-right: auto; letter-spacing: 0.3px; }
    .hero { background: linear-gradient(135deg, #2d5a3d 0%, #3a7a52 60%, #4f9b6b 100%);
            padding: 80px 40px; text-align: center; color: #fff; }
    .hero h1 { font-size: 2.6em; margin-bottom: 12px; font-weight: 600; }
    .hero p { font-size: 1.1em; color: #d8efd8; max-width: 640px; margin: 0 auto; }
    .content { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 8px; padding: 28px; margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .card h2 { color: #2d5a3d; margin-bottom: 14px; }
    .card h3 { color: #3a6e4a; margin-bottom: 10px; margin-top: 16px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
    .footer { text-align: center; padding: 30px; color: #7a8c7a; font-size: 0.85em;
              border-top: 1px solid #d0e0d0; margin-top: 50px; background: #fff; }
    .footer a { color: #2d5a3d; text-decoration: none; }
    .login-container { max-width: 420px; margin: 80px auto; }
    .login-box { background: #fff; border-radius: 8px; padding: 36px;
                 box-shadow: 0 4px 18px rgba(0,0,0,0.12); }
    .login-box h2 { text-align: center; color: #2d5a3d; margin-bottom: 22px; }
    .login-box input { width: 100%%; padding: 11px; margin: 7px 0; border: 1px solid #cfd8d0;
                       border-radius: 5px; font-size: 0.95em; }
    .login-box button { width: 100%%; padding: 11px; background: #2d5a3d; color: #fff;
                        border: none; border-radius: 5px; font-size: 1em; cursor: pointer;
                        margin-top: 14px; font-weight: 600; }
    .login-box button:hover { background: #3a7a52; }
    .error { color: #c0392b; text-align: center; margin-bottom: 12px; font-size: 0.88em; }
    .dash-header { background: #2d5a3d; color: #fff; padding: 22px 40px; }
    .dash-header h1 { font-size: 1.4em; }
    .dash-header span { color: #f4d35e; }
    .dash-body { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
    table { width: 100%%; border-collapse: collapse; }
    table th { background: #f1f5f1; padding: 12px; text-align: left; font-size: 0.82em;
               color: #5a6a5a; text-transform: uppercase; letter-spacing: 0.5px; }
    table td { padding: 12px; border-bottom: 1px solid #ecf0ec; }
    .badge { display: inline-block; padding: 3px 11px; border-radius: 12px; font-size: 0.78em; font-weight: 600; }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-blue { background: #d1ecf1; color: #0c5460; }
    .badge-red { background: #f8d7da; color: #721c24; }
    .config-block { background: #f1f5f1; border: 1px solid #cfd8d0; border-radius: 5px;
                    padding: 14px; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.85em; margin: 12px 0;
                    white-space: pre-wrap; color: #2c3e2c; }
    .news-item { padding: 18px; border-bottom: 1px solid #ecf0ec; }
    .news-item:last-child { border-bottom: none; }
    .news-item h3 { color: #2d5a3d; }
    .news-item .meta { color: #7a8c7a; font-size: 0.85em; margin: 6px 0 12px; }
    .news-item a { color: #2d5a3d; text-decoration: none; font-weight: 600; }
    .provider-card { padding: 16px; border: 1px solid #ecf0ec; border-radius: 6px; margin: 10px 0; }
    .provider-card .name { font-weight: 700; color: #2d5a3d; font-size: 1.05em; }
    .provider-card .spec { color: #5a6a5a; font-size: 0.9em; margin-top: 4px; }
    .form-item { padding: 12px; border-bottom: 1px solid #ecf0ec; display: flex; justify-content: space-between; }
    .form-item:last-child { border-bottom: none; }
    .form-item .name { color: #2d5a3d; font-weight: 600; }
    .form-item .size { color: #7a8c7a; font-size: 0.85em; }
</style>
"""

NAV = """
<nav class="nav">
    <a href="/" class="brand">Pinecrest Family Practice</a>
    <a href="/">Home</a>
    <a href="/providers">Providers</a>
    <a href="/services">Services</a>
    <a href="/forms/">Patient Forms</a>
    <a href="/insurance">Insurance</a>
    <a href="/news/">News</a>
    <a href="/contact">Contact</a>
</nav>
"""

FOOTER = """
<div class="footer">
    &copy; 2025 Pinecrest Family Practice, P.A. All rights reserved.<br>
    <a href="/privacy">HIPAA Notice of Privacy Practices</a> &bull; <a href="/terms">Terms</a> &bull; <a href="/patient-portal/">Patient Portal</a><br>
    1840 Hawthorne Ln, Charlotte, NC 28204 &bull; (704) 555-0166
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
    return page("Pinecrest Family Practice", """
<div class="hero">
    <h1>Pinecrest Family Practice</h1>
    <p>Family medicine, pediatrics, internal medicine, and geriatrics in the heart of Charlotte.</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Compassionate Primary Care</h2>
            <p>Six providers serving patients of every age. We focus on long-term relationships and continuity of care across generations.</p>
        </div>
        <div class="card">
            <h2>Same-Day Sick Visits</h2>
            <p>Same-day appointment slots reserved every weekday morning. Call before 9 a.m. to be seen the same day.</p>
        </div>
        <div class="card">
            <h2>Onsite Lab Draws</h2>
            <p>Quest Diagnostics lab draws available onsite Monday through Friday. Most insurance plans accepted.</p>
        </div>
    </div>
    <div class="card">
        <h2>Welcome to Pinecrest</h2>
        <p>Pinecrest Family Practice has been serving Charlotte families since 1996. Our practice was founded by Dr. Helena Yasin and has grown to a six-provider team committed to evidence-based primary care for the Eastover, Plaza Midwood, and Myers Park neighborhoods.</p>
        <br>
        <p>If you are a new patient, please call our office at (704) 555-0166 or use the patient portal link in the footer to schedule your first visit. We look forward to caring for you.</p>
    </div>
</div>
""")


@app.route("/providers")
def providers():
    return page("Providers - Pinecrest Family Practice", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Our Providers</h2>
        <p>Pinecrest Family Practice has six board-certified providers covering family medicine, pediatrics, internal medicine, and geriatrics. New patients are welcome.</p>
        <br>
        <div class="provider-card">
            <div class="name">Dr. Helena Yasin, MD</div>
            <div class="spec">Family Medicine &bull; Founder &bull; Accepting new patients</div>
            <p style="margin-top:8px; color:#5a6a5a;">Dr. Yasin founded Pinecrest in 1996 after completing her residency at UNC. She specializes in long-term primary care relationships and chronic disease management.</p>
        </div>
        <div class="provider-card">
            <div class="name">Dr. Marcus Brennan, MD</div>
            <div class="spec">Pediatrics &bull; Accepting new patients (ages newborn to 18)</div>
            <p style="margin-top:8px; color:#5a6a5a;">Dr. Brennan joined the practice in 2020. He completed his pediatric residency at Vanderbilt and has a particular interest in adolescent mental health.</p>
        </div>
        <div class="provider-card">
            <div class="name">Dr. Aisha Patel-Rao, MD</div>
            <div class="spec">Internal Medicine &bull; Accepting new patients</div>
            <p style="margin-top:8px; color:#5a6a5a;">Dr. Patel-Rao is board-certified in internal medicine and has been with Pinecrest since 2018. She focuses on hypertension, diabetes management, and preventive care.</p>
        </div>
        <div class="provider-card">
            <div class="name">Dr. Theo Wei, MD</div>
            <div class="spec">Family Medicine &bull; Accepting new patients</div>
            <p style="margin-top:8px; color:#5a6a5a;">Dr. Wei joined Pinecrest in 2022. His practice covers all ages with a focus on sports medicine and musculoskeletal complaints.</p>
        </div>
        <div class="provider-card">
            <div class="name">Dr. Devin Lassiter, MD</div>
            <div class="spec">Geriatrics &bull; Accepting new patients (ages 65 and older)</div>
            <p style="margin-top:8px; color:#5a6a5a;">Dr. Lassiter is fellowship-trained in geriatric medicine and joined Pinecrest in 2023. His practice covers cognitive assessment, polypharmacy review, and end-of-life planning.</p>
        </div>
        <div class="provider-card">
            <div class="name">Sandra Pham, NP</div>
            <div class="spec">Adult Primary Care &bull; Accepting new patients</div>
            <p style="margin-top:8px; color:#5a6a5a;">Sandra is a board-certified family nurse practitioner. She works closely with Dr. Patel-Rao on chronic disease management and routine adult care.</p>
        </div>
    </div>
</div>
""")


@app.route("/services")
def services():
    return page("Services - Pinecrest Family Practice", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Services Offered</h2>
        <ul style="line-height: 1.9; padding-left: 22px;">
            <li><strong>Routine Wellness Visits</strong> &bull; annual physicals, well-child visits, Medicare wellness exams</li>
            <li><strong>Acute Care</strong> &bull; same-day appointments for sick visits, minor injuries, and urgent concerns</li>
            <li><strong>Chronic Disease Management</strong> &bull; hypertension, diabetes, COPD, asthma, thyroid disorders</li>
            <li><strong>Pediatric Care</strong> &bull; newborn visits, vaccinations, school physicals, adolescent care</li>
            <li><strong>Geriatric Care</strong> &bull; cognitive assessment, fall risk, polypharmacy review</li>
            <li><strong>Preventive Care</strong> &bull; cancer screening, immunizations, lifestyle counseling</li>
            <li><strong>Onsite Lab</strong> &bull; Quest Diagnostics blood draws Monday through Friday</li>
            <li><strong>Mental Health Support</strong> &bull; depression and anxiety screening, referral to in-network specialists</li>
            <li><strong>Telemedicine</strong> &bull; secure video visits for established patients</li>
        </ul>
    </div>
</div>
""")


@app.route("/insurance")
def insurance():
    return page("Insurance - Pinecrest Family Practice", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Accepted Insurance Plans</h2>
        <p>Pinecrest Family Practice is in-network with the following plans. Please verify benefits with your insurer before your visit.</p>
        <br>
        <ul style="line-height: 1.9; padding-left: 22px;">
            <li>Aetna (Commercial, Medicare Advantage)</li>
            <li>Blue Cross Blue Shield of North Carolina</li>
            <li>Cigna</li>
            <li>Humana (Commercial, Medicare Advantage)</li>
            <li>Medicare (Traditional Part B)</li>
            <li>NC Medicaid (selected plans)</li>
            <li>UnitedHealthcare (Commercial, Medicare Advantage)</li>
            <li>WellCare Medicare Advantage</li>
        </ul>
        <br>
        <p>If your plan is not listed, please call the office at (704) 555-0166 to confirm coverage.</p>
    </div>
    <div class="card">
        <h2>Self-Pay</h2>
        <p>We accept self-pay patients. Visit fees are posted at the front desk and on request. Payment is expected at time of service unless prior arrangements have been made.</p>
    </div>
</div>
""")


@app.route("/forms/")
def forms_index():
    return page("Patient Forms - Pinecrest", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Patient Forms</h2>
        <p>Download and complete the relevant forms before your visit to save time at check-in.</p>
        <br>
        <div class="form-item">
            <span class="name">New Patient Intake (PDF)</span>
            <span class="size">412 KB</span>
        </div>
        <div class="form-item">
            <span class="name">Authorization for Release of Medical Records (PDF)</span>
            <span class="size">186 KB</span>
        </div>
        <div class="form-item">
            <span class="name">Pediatric Well-Child History (PDF)</span>
            <span class="size">298 KB</span>
        </div>
        <div class="form-item">
            <span class="name">Medicare Annual Wellness Questionnaire (PDF)</span>
            <span class="size">221 KB</span>
        </div>
        <div class="form-item">
            <span class="name">Adult Depression Screening (PHQ-9)</span>
            <span class="size">88 KB</span>
        </div>
        <div class="form-item">
            <span class="name">Adult Anxiety Screening (GAD-7)</span>
            <span class="size">82 KB</span>
        </div>
        <div class="form-item">
            <span class="name">HIPAA Notice of Privacy Practices Acknowledgement</span>
            <span class="size">94 KB</span>
        </div>
    </div>
    <div class="card">
        <p style="color:#7a8c7a; font-size:0.88em;">Forms are also available at the front desk. If you cannot complete a form before your visit, please arrive fifteen minutes early to complete it onsite.</p>
    </div>
</div>
""")


@app.route("/news/")
def news_index():
    return page("News - Pinecrest", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Practice News</h2>
        <div class="news-item">
            <h3><a href="/news/2025-flu-shot-clinic/">2025-2026 Flu Shot Clinic Now Open</a></h3>
            <div class="meta">October 6, 2025 &bull; Preventive Care</div>
            <p>Flu shots are available at every visit and during dedicated walk-in clinic hours every Wednesday afternoon through December. No appointment needed during the walk-in window...</p>
        </div>
        <div class="news-item">
            <h3><a href="/news/2025-mychart-launch/">Pinecrest Has Launched MyChart</a></h3>
            <div class="meta">August 11, 2025 &bull; Patient Experience</div>
            <p>Patients can now message their providers, view lab results, request prescription refills, and schedule appointments through MyChart. Activation codes are sent by email after your next visit...</p>
        </div>
        <div class="news-item">
            <h3><a href="/news/2024-new-pediatrician/">Welcome Dr. Marcus Brennan to Our Pediatric Team</a></h3>
            <div class="meta">June 2, 2024 &bull; Practice Update</div>
            <p>Pinecrest is delighted to welcome Dr. Marcus Brennan to our pediatric team. Dr. Brennan completed his residency at Vanderbilt and joins us with a particular interest in adolescent mental health...</p>
        </div>
        <div class="news-item">
            <h3><a href="/news/2024-renovation-complete/">Lobby Renovation Complete</a></h3>
            <div class="meta">February 18, 2024 &bull; Facilities</div>
            <p>Our lobby renovation is complete. The waiting area has been refreshed with new seating, additional charging outlets, and improved acoustic separation between the waiting and check-in areas...</p>
        </div>
    </div>
</div>
""")


@app.route("/news/2025-flu-shot-clinic/")
def news_flu():
    return page("Flu Shot Clinic - Pinecrest", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>2025-2026 Flu Shot Clinic Now Open</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">October 6, 2025 &bull; Preventive Care</div>
        <p>Flu shots are available at every visit and during dedicated walk-in clinic hours every Wednesday afternoon through December. No appointment needed during the walk-in window. Adults and children ages six months and older can be vaccinated.</p>
        <br>
        <p>This year we are offering both the standard flu vaccine and the high-dose vaccine for adults age 65 and older. The flu vaccine is covered by most insurance plans. Self-pay pricing is posted at the front desk.</p>
        <br>
        <p>Walk-in hours: every Wednesday from 1 p.m. to 5 p.m. through December 17, 2025.</p>
    </div>
</div>
""")


@app.route("/news/2025-mychart-launch/")
def news_mychart():
    return page("MyChart Launch - Pinecrest", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Pinecrest Has Launched MyChart</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">August 11, 2025 &bull; Patient Experience</div>
        <p>Patients can now message their providers, view lab results, request prescription refills, and schedule appointments through MyChart. Activation codes are sent by email after your next visit. If you do not receive a code, please call the front desk.</p>
        <br>
        <p>MyChart replaces the older internal patient portal we previously used. The old portal has been retired and will be removed from this site at our next maintenance window.</p>
    </div>
</div>
""")


@app.route("/news/2024-new-pediatrician/")
def news_brennan():
    return page("Dr. Marcus Brennan - Pinecrest", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Welcome Dr. Marcus Brennan to Our Pediatric Team</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">June 2, 2024 &bull; Practice Update</div>
        <p>Pinecrest is delighted to welcome Dr. Marcus Brennan to our pediatric team. Dr. Brennan completed his residency at Vanderbilt and joins us with a particular interest in adolescent mental health. He is now accepting new patients ages newborn through eighteen.</p>
        <br>
        <p>Dr. Brennan is in the office Monday through Friday with same-day pediatric sick visits available every morning.</p>
    </div>
</div>
""")


@app.route("/news/2024-renovation-complete/")
def news_renovation():
    return page("Lobby Renovation - Pinecrest", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Lobby Renovation Complete</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">February 18, 2024 &bull; Facilities</div>
        <p>Our lobby renovation is complete. The waiting area has been refreshed with new seating, additional charging outlets, and improved acoustic separation between the waiting and check-in areas. Thank you to our patients for their patience during the project.</p>
    </div>
</div>
""")


@app.route("/contact")
def contact():
    return page("Contact - Pinecrest Family Practice", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Contact Us</h2>
        <p><strong>Address:</strong> 1840 Hawthorne Ln, Charlotte, NC 28204<br>
        <strong>Phone:</strong> (704) 555-0166<br>
        <strong>Fax:</strong> (704) 555-0167<br>
        <strong>After-hours nurse line:</strong> (704) 555-0166 (option 4)</p>
        <br>
        <p><strong>Office hours:</strong><br>
        Monday through Friday, 7:30 a.m. to 5:30 p.m.<br>
        Wednesday extended hours until 7:00 p.m.<br>
        Saturday, 9:00 a.m. to 12:00 p.m. (urgent only)</p>
    </div>
</div>
""")


@app.route("/privacy")
def privacy():
    return page("HIPAA Notice - Pinecrest", """
<div class="content" style="margin-top:40px;"><div class="card">
<h2>HIPAA Notice of Privacy Practices</h2>
<p>This notice describes how medical information about you may be used and disclosed and how you can get access to this information. Please review carefully.</p>
<br>
<p>Pinecrest Family Practice is required by federal law to maintain the privacy of your protected health information (PHI), provide you with this notice of our legal duties and privacy practices regarding PHI, notify you in the event of a breach of unsecured PHI, and follow the terms of the notice currently in effect.</p>
<br>
<p>Full text of the HIPAA Notice of Privacy Practices is available at the front desk and on request.</p>
</div></div>
""")


@app.route("/terms")
def terms():
    return page("Terms - Pinecrest", """
<div class="content" style="margin-top:40px;"><div class="card">
<h2>Terms of Use</h2>
<p>Use of this website is subject to the terms below. The website is for informational purposes only and does not provide medical advice. If you are experiencing a medical emergency, call 911.</p>
</div></div>
""")


@app.route("/patient-portal/")
def patient_portal_redirect():
    return page("Patient Portal - Pinecrest", """
<div class="content" style="margin-top:40px;"><div class="card">
<h2>Patient Portal</h2>
<p>Pinecrest patient access has moved to MyChart. Please visit <strong>mychart.pinecrestfp.com</strong> to log in or activate your account.</p>
<br>
<p>If you have not yet received your MyChart activation code, please call the front desk at (704) 555-0166.</p>
<br>
<p style="color:#7a8c7a; font-size:0.85em;">Note: this page replaced our old internal patient portal in August 2025.</p>
</div></div>
""")


# Robots.txt - the discovery hint for the staff portal

@app.route("/robots.txt")
def robots():
    return """User-agent: *
Disallow: /staff/
Disallow: /api/
Disallow: /old-portal/
""", 200, {"Content-Type": "text/plain"}


# Decoy / red herring routes

@app.route("/api/")
def api_root():
    return '{"error":"unauthorized","message":"This API requires a Pinecrest staff bearer token."}', 401, {"Content-Type": "application/json"}


@app.route("/api/v2/health")
def api_v2_health():
    return '{"status":"ok","service":"pinecrest-staff","version":"1.6.4"}', 200, {"Content-Type": "application/json"}


@app.route("/old-portal/")
def old_portal():
    return "404 Not Found", 404


@app.route("/admin")
@app.route("/admin/")
def admin_redirect():
    return redirect("/staff/")


# Staff Portal: the actual vulnerable target

@app.route("/staff/")
def staff_login():
    error_msg = ""
    if request.args.get("error"):
        error_msg = '<p class="error">Login failed. Check your credentials.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Pinecrest Staff</title>{STYLE}</head>
<body style="background:#2d5a3d;">
<div class="login-container">
    <div class="login-box">
        <h2>Pinecrest Staff Login</h2>
        {error_msg}
        <form method="POST" action="/staff/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <p style="text-align:center; margin-top:18px; font-size:0.78em; color:#999;">
            Authorized staff only. Unauthorized access is prohibited.
        </p>
    </div>
</div>
</body></html>"""


def _try_sqli_login(username, password):
    # VULNERABLE: SQL query built with string formatting against in-memory
    # sqlite. Retry with MySQL-style # comments rewritten to ANSI -- so
    # SQLi payloads written for any common backend dialect succeed.
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


@app.route("/staff/login", methods=["POST"])
def staff_do_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    row = _try_sqli_login(username, password)
    if row:
        resp = make_response(redirect("/staff/dashboard"))
        resp.set_cookie("pcfp_session", "authenticated_staff_v1")
        return resp
    return redirect("/staff/?error=1")


@app.route("/staff/dashboard")
def staff_dashboard():
    if request.cookies.get("pcfp_session") != "authenticated_staff_v1":
        return redirect("/staff/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Staff Dashboard - Pinecrest</title>{STYLE}</head>
<body>
<div class="dash-header">
    <h1>Pinecrest <span>Staff Dashboard</span></h1>
</div>
<div class="dash-body">
    <div class="card">
        <h2>System Overview</h2>
        <table>
            <tr><th>Component</th><th>Status</th><th>Detail</th></tr>
            <tr><td>Staff Portal</td><td><span class="badge badge-green">Online</span></td><td>v1.6.4 (legacy)</td></tr>
            <tr><td>MyChart Sync</td><td><span class="badge badge-red">Disabled</span></td><td>Decommissioned 2025-08</td></tr>
            <tr><td>Equipment Asset Token</td><td><span class="badge badge-yellow">Active</span></td><td><code>{WEB_TOKEN}</code></td></tr>
            <tr><td>SMB Integration</td><td><span class="badge badge-green">Connected</span></td><td>pinecrest-fs01</td></tr>
        </table>
    </div>
    <div class="card">
        <h2>Today's Schedule (sample)</h2>
        <table>
            <tr><th>Time</th><th>Provider</th><th>Patient</th><th>Visit Type</th></tr>
            <tr><td>8:00 AM</td><td>Dr. Yasin</td><td>(redacted)</td><td>Annual Physical</td></tr>
            <tr><td>8:30 AM</td><td>Dr. Brennan</td><td>(redacted)</td><td>Pediatric Wellness</td></tr>
            <tr><td>9:00 AM</td><td>Dr. Patel-Rao</td><td>(redacted)</td><td>Diabetes Follow-up</td></tr>
            <tr><td>9:30 AM</td><td>Dr. Wei</td><td>(redacted)</td><td>Acute Sick Visit</td></tr>
            <tr><td>10:00 AM</td><td>Dr. Lassiter</td><td>(redacted)</td><td>Geriatric Wellness</td></tr>
        </table>
        <p style="color:#7a8c7a; font-size:0.85em; margin-top:12px;">Patient names are not stored in this portal. The actual schedule lives in the EHR. This page renders sample placeholders only.</p>
    </div>
    <div class="card">
        <h2>Application Configuration</h2>
        <p style="color:#7a8c7a; font-size:0.9em;">Read-only view of the running configuration.</p>
        <div class="config-block">APP_ENV=production
APP_VERSION=1.6.4
APP_OWNER=Pinecrest Family Practice
DB_DRIVER=sqlite
DB_PATH=/var/lib/pcfp/staff.db
SMB_HOST=pinecrest-fs01
SMB_BACKUP_USER=clinic_archivist
LOG_LEVEL=info
DECOMMISSION_TARGET=2025-12-31</div>
        <p style="color:#c0392b; font-size:0.8em; margin-top:10px;">
            &#9888; This portal was scheduled for decommission in 2025. See ticket queue for status.
        </p>
    </div>
</div>
{FOOTER}
</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
