"""
Kestrel Architecture Studio - Internal Project CMS

Deliberately vulnerable Flask app for the Week 15 mock final.
Multiple legitimate-looking pages plus a hidden staff portal at /staff/
that accepts a SQL injection authentication bypass.

Same skill chain as the Pinecrest final exam; different scenario,
paths, content, and flag values. Token from this app is the FIRST
token in the assembled flag.
"""

import sqlite3
from flask import Flask, request, redirect, make_response

app = Flask(__name__)

WEB_TOKEN = "token=dr4ft"


def get_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE staff (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    cur.execute("INSERT INTO staff VALUES (1, 'admin', 'K3str3lAdm2024', 'administrator')")
    cur.execute("INSERT INTO staff VALUES (2, 'bhalloran', 'StudioIT_2024', 'contractor')")
    cur.execute("INSERT INTO staff VALUES (3, 'mwhittaker', 'MargoW_2024#', 'partner')")
    cur.execute("INSERT INTO staff VALUES (4, 'rdewitt', 'RobinD#2025', 'staff')")
    conn.commit()
    return conn


STYLE = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #f7f5f2; color: #2a2622; }
    .nav { background: #1f2933; padding: 14px 40px; display: flex; align-items: center; gap: 28px; }
    .nav a { color: #c8ccd2; text-decoration: none; font-size: 0.95em; }
    .nav a:hover { color: #fff; }
    .nav .brand { color: #d6a55c; font-weight: 700; font-size: 1.18em; margin-right: auto; letter-spacing: 0.4px; }
    .hero { background: linear-gradient(135deg, #1f2933 0%, #364152 60%, #4a5568 100%);
            padding: 90px 40px; text-align: center; color: #fff; }
    .hero h1 { font-size: 2.7em; margin-bottom: 14px; font-weight: 600; letter-spacing: 0.5px; }
    .hero p { font-size: 1.12em; color: #d8dde6; max-width: 660px; margin: 0 auto; }
    .content { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 6px; padding: 28px; margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .card h2 { color: #1f2933; margin-bottom: 14px; }
    .card h3 { color: #364152; margin-bottom: 10px; margin-top: 16px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
    .footer { text-align: center; padding: 30px; color: #7a7066; font-size: 0.85em;
              border-top: 1px solid #e0d8cc; margin-top: 50px; background: #fff; }
    .footer a { color: #1f2933; text-decoration: none; }
    .login-container { max-width: 420px; margin: 80px auto; }
    .login-box { background: #fff; border-radius: 6px; padding: 36px;
                 box-shadow: 0 4px 18px rgba(0,0,0,0.18); }
    .login-box h2 { text-align: center; color: #1f2933; margin-bottom: 22px; }
    .login-box input { width: 100%%; padding: 11px; margin: 7px 0; border: 1px solid #d6cfc4;
                       border-radius: 4px; font-size: 0.95em; }
    .login-box button { width: 100%%; padding: 11px; background: #1f2933; color: #fff;
                        border: none; border-radius: 4px; font-size: 1em; cursor: pointer;
                        margin-top: 14px; font-weight: 600; letter-spacing: 0.3px; }
    .login-box button:hover { background: #364152; }
    .error { color: #b34d3f; text-align: center; margin-bottom: 12px; font-size: 0.88em; }
    .dash-header { background: #1f2933; color: #fff; padding: 22px 40px; }
    .dash-header h1 { font-size: 1.4em; }
    .dash-header span { color: #d6a55c; }
    .dash-body { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
    table { width: 100%%; border-collapse: collapse; }
    table th { background: #f1ede5; padding: 12px; text-align: left; font-size: 0.82em;
               color: #5a534a; text-transform: uppercase; letter-spacing: 0.5px; }
    table td { padding: 12px; border-bottom: 1px solid #ece6d9; }
    .badge { display: inline-block; padding: 3px 11px; border-radius: 12px; font-size: 0.78em; font-weight: 600; }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-blue { background: #d1ecf1; color: #0c5460; }
    .badge-red { background: #f8d7da; color: #721c24; }
    .config-block { background: #f1ede5; border: 1px solid #d6cfc4; border-radius: 4px;
                    padding: 14px; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.85em; margin: 12px 0;
                    white-space: pre-wrap; color: #2a2622; }
    .project-card { padding: 16px; border: 1px solid #ece6d9; border-radius: 5px; margin: 10px 0; }
    .project-card .num { color: #d6a55c; font-weight: 700; font-size: 0.9em; letter-spacing: 0.5px; }
    .project-card .title { font-weight: 700; color: #1f2933; font-size: 1.1em; margin-top: 4px; }
    .project-card .meta { color: #5a534a; font-size: 0.88em; margin-top: 4px; }
    .person-card { padding: 14px; border: 1px solid #ece6d9; border-radius: 5px; margin: 10px 0; }
    .person-card .name { font-weight: 700; color: #1f2933; font-size: 1.05em; }
    .person-card .role { color: #5a534a; font-size: 0.9em; margin-top: 4px; }
    .news-item { padding: 18px; border-bottom: 1px solid #ece6d9; }
    .news-item:last-child { border-bottom: none; }
    .news-item h3 { color: #1f2933; }
    .news-item .meta { color: #7a7066; font-size: 0.85em; margin: 6px 0 12px; }
    .news-item a { color: #1f2933; text-decoration: none; font-weight: 600; }
</style>
"""

NAV = """
<nav class="nav">
    <a href="/" class="brand">Kestrel Architecture Studio</a>
    <a href="/">Home</a>
    <a href="/projects">Projects</a>
    <a href="/team">Team</a>
    <a href="/services">Services</a>
    <a href="/journal/">Journal</a>
    <a href="/careers">Careers</a>
    <a href="/contact">Contact</a>
</nav>
"""

FOOTER = """
<div class="footer">
    &copy; 2025 Kestrel Architecture Studio, P.C.<br>
    <a href="/journal/">Studio Journal</a> &bull; <a href="/careers">Careers</a> &bull; <a href="/contact">Contact</a><br>
    1024 NW Flanders St, Portland, OR 97209 &bull; (503) 555-0166
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
    return page("Kestrel Architecture Studio", """
<div class="hero">
    <h1>Kestrel Architecture Studio</h1>
    <p>Civic, residential, and small commercial architecture in the Pacific Northwest. Founded in Portland, 2014.</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card">
            <h2>Place-Driven Design</h2>
            <p>Every project starts with the climate, the neighbors, and the way people actually move through a space. We design for the long arc of a building, not just the ribbon cutting.</p>
        </div>
        <div class="card">
            <h2>Small Studio, Wide Reach</h2>
            <p>A team of twelve architects and designers. Twenty-eight projects delivered across Oregon and Southwest Washington in the past five years.</p>
        </div>
        <div class="card">
            <h2>Civic and Residential</h2>
            <p>Civic libraries and pavilions, single-family residences, and small commercial tenant improvements. We turn down work outside our core competencies.</p>
        </div>
    </div>
    <div class="card">
        <h2>About Kestrel</h2>
        <p>Kestrel Architecture Studio was founded by Margo Whittaker in 2014 and has grown to a twelve-person practice serving clients across the Pacific Northwest. We focus on the kinds of projects where careful detailing and quiet spatial moves matter more than grand gestures.</p>
        <br>
        <p>If you are considering a project, please use the contact form or call our studio at (503) 555-0166. We respond to inquiries within two business days.</p>
    </div>
</div>
""")


@app.route("/projects")
def projects():
    return page("Projects - Kestrel Architecture Studio", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Selected Projects</h2>
        <p>A small selection of recently delivered work. The full project archive is available on request.</p>
        <br>
        <div class="project-card">
            <div class="num">25-009</div>
            <div class="title">Albina Mixed Use, Phase I</div>
            <div class="meta">Mixed Use &bull; Portland, OR &bull; In Construction</div>
            <p style="margin-top:10px; color:#5a534a;">A four-story mixed-use building combining ground-floor retail with thirty-two affordable housing units above. Cross-laminated timber structure on a concrete podium.</p>
        </div>
        <div class="project-card">
            <div class="num">25-002</div>
            <div class="title">Northwest Library Expansion</div>
            <div class="meta">Civic &bull; Hillsboro, OR &bull; Construction Complete 2025-09</div>
            <p style="margin-top:10px; color:#5a534a;">A 4,200 square foot expansion to a Carnegie-era branch library. New children's wing, accessible reading garden, and seismic upgrade to the original building.</p>
        </div>
        <div class="project-card">
            <div class="num">24-022</div>
            <div class="title">Beaverton Mews Townhomes</div>
            <div class="meta">Residential MFR &bull; Beaverton, OR &bull; Delivered 2024-Q4</div>
            <p style="margin-top:10px; color:#5a534a;">Eight townhome units arranged around a shared mews. Passive House certified envelope, ground source heat pumps, photovoltaic array on the roofs.</p>
        </div>
        <div class="project-card">
            <div class="num">24-031</div>
            <div class="title">Forest Park Trail Pavilion</div>
            <div class="meta">Civic &bull; Portland, OR &bull; Delivered 2024-Q2</div>
            <p style="margin-top:10px; color:#5a534a;">A small open-air pavilion serving as a wayfinding and rest stop on the Wildwood Trail. Locally sourced douglas fir frame with a corten steel roof.</p>
        </div>
    </div>
</div>
""")


@app.route("/team")
def team():
    return page("Team - Kestrel Architecture Studio", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Studio Team</h2>
        <p>Twelve architects and designers, plus our office coordinator and bookkeeper.</p>
        <br>
        <div class="person-card">
            <div class="name">Margo Whittaker, AIA</div>
            <div class="role">Managing Partner &bull; Founded the studio in 2014</div>
        </div>
        <div class="person-card">
            <div class="name">Daniel Okonkwo, AIA</div>
            <div class="role">Senior Architect &bull; Civic and mixed-use lead</div>
        </div>
        <div class="person-card">
            <div class="name">Priya Ramaswamy, AIA</div>
            <div class="role">Senior Architect &bull; Residential and small commercial lead</div>
        </div>
        <div class="person-card">
            <div class="name">Theo Lindqvist, AIA</div>
            <div class="role">Architect</div>
        </div>
        <div class="person-card">
            <div class="name">Hana Sato, AIA</div>
            <div class="role">Architect</div>
        </div>
        <div class="person-card">
            <div class="name">Jules Bertrand</div>
            <div class="role">Project Architect</div>
        </div>
        <div class="person-card">
            <div class="name">Grace Halloran &bull; Aiden Wexler &bull; Mira Castellanos &bull; Quinn Faraday</div>
            <div class="role">Designers</div>
        </div>
    </div>
</div>
""")


@app.route("/services")
def services():
    return page("Services - Kestrel Architecture Studio", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Services</h2>
        <ul style="line-height: 1.9; padding-left: 22px;">
            <li><strong>Feasibility and Programming</strong> &bull; site analysis, zoning review, program development</li>
            <li><strong>Schematic Design</strong> &bull; massing studies, site planning, early renderings</li>
            <li><strong>Design Development</strong> &bull; material selection, wall sections, consultant coordination</li>
            <li><strong>Construction Documents</strong> &bull; signed and sealed permit and bid sets</li>
            <li><strong>Permitting</strong> &bull; submittal preparation, plan check response, agency coordination</li>
            <li><strong>Construction Administration</strong> &bull; site visits, RFI and submittal review, punch list</li>
            <li><strong>Adaptive Reuse and Renovation</strong> &bull; existing-building documentation, code analysis</li>
            <li><strong>Sustainability Consulting</strong> &bull; Passive House design, embodied carbon assessment</li>
        </ul>
    </div>
</div>
""")


@app.route("/journal/")
def journal_index():
    return page("Journal - Kestrel", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Studio Journal</h2>
        <div class="news-item">
            <h3><a href="/journal/2025-northwest-library-opens/">Northwest Library Expansion Opens to the Public</a></h3>
            <div class="meta">September 18, 2025 &bull; Project Update</div>
            <p>The expansion to the Carnegie-era branch library officially opened with a ribbon cutting attended by city council members and the Friends of the Library. The new children's wing nearly doubles the dedicated reading space...</p>
        </div>
        <div class="news-item">
            <h3><a href="/journal/2025-newforma-cutover/">Studio Operations Migrating to Newforma</a></h3>
            <div class="meta">March 5, 2025 &bull; Studio Update</div>
            <p>Active project files have moved to Newforma. The transition consolidates project management, file sharing, and consultant coordination into one platform. Older closed-project archives remain on the studio file server for the time being...</p>
        </div>
        <div class="news-item">
            <h3><a href="/journal/2024-passive-house-certification/">Beaverton Mews Achieves Passive House Certification</a></h3>
            <div class="meta">November 12, 2024 &bull; Project Milestone</div>
            <p>The eight-unit townhome project in Beaverton received its final Passive House Institute US (PHIUS) certification this week. Air leakage testing came in well below the certification threshold...</p>
        </div>
        <div class="news-item">
            <h3><a href="/journal/2024-pavilion-completion/">Forest Park Trail Pavilion Complete</a></h3>
            <div class="meta">May 22, 2024 &bull; Project Update</div>
            <p>The wayfinding pavilion on the Wildwood Trail is open to hikers. The corten steel roof has begun to take on its weathered patina and the douglas fir frame is settling in well to the forest setting...</p>
        </div>
    </div>
</div>
""")


@app.route("/journal/2025-northwest-library-opens/")
def journal_library():
    return page("Northwest Library Expansion - Kestrel", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Northwest Library Expansion Opens to the Public</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">September 18, 2025 &bull; Project Update</div>
        <p>The expansion to the Carnegie-era branch library officially opened with a ribbon cutting attended by city council members and the Friends of the Library. The new children's wing nearly doubles the dedicated reading space and provides a separate program room that can be reserved for after-school tutoring.</p>
        <br>
        <p>The seismic retrofit to the original 1912 structure was the largest single line item in the project budget. The exterior masonry was preserved through careful coordination with the structural engineer and the local masonry contractor.</p>
    </div>
</div>
""")


@app.route("/journal/2025-newforma-cutover/")
def journal_newforma():
    return page("Newforma Cutover - Kestrel", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Studio Operations Migrating to Newforma</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">March 5, 2025 &bull; Studio Update</div>
        <p>Active project files have moved to Newforma. The transition consolidates project management, file sharing, and consultant coordination into one platform. Older closed-project archives remain on the studio file server for the time being while we confirm the migration approach.</p>
        <br>
        <p>The internal project tracking tool we used previously will be retired once the closed-project migration is complete. No firm date has been set.</p>
    </div>
</div>
""")


@app.route("/journal/2024-passive-house-certification/")
def journal_phius():
    return page("Beaverton Mews Passive House - Kestrel", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Beaverton Mews Achieves Passive House Certification</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">November 12, 2024 &bull; Project Milestone</div>
        <p>The eight-unit townhome project in Beaverton received its final Passive House Institute US (PHIUS) certification this week. Air leakage testing came in well below the certification threshold, a credit to the careful work of the framing and air-sealing crews.</p>
    </div>
</div>
""")


@app.route("/journal/2024-pavilion-completion/")
def journal_pavilion():
    return page("Forest Park Pavilion - Kestrel", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Forest Park Trail Pavilion Complete</h2>
        <div class="news-item meta" style="border:none; padding:0; margin-bottom:18px;">May 22, 2024 &bull; Project Update</div>
        <p>The wayfinding pavilion on the Wildwood Trail is open to hikers. The corten steel roof has begun to take on its weathered patina and the douglas fir frame is settling in well to the forest setting.</p>
    </div>
</div>
""")


@app.route("/careers")
def careers():
    return page("Careers - Kestrel", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Careers at Kestrel</h2>
        <p>We hire one or two people most years and we hire deliberately. Open positions are listed below. If nothing here fits, we still welcome introductions and keep applications on file for twelve months.</p>
        <br>
        <h3>Project Architect (3 to 6 years experience)</h3>
        <p>You will lead small commercial and residential projects from schematic design through construction administration. Licensure or active path to licensure required. Send portfolio and resume to careers via the contact form.</p>
        <br>
        <h3>Designer (0 to 3 years experience)</h3>
        <p>You will support project teams across all phases with a focus on Revit modeling, drawing production, and rendering. Bachelor or master of architecture required.</p>
    </div>
</div>
""")


@app.route("/contact")
def contact():
    return page("Contact - Kestrel Architecture Studio", """
<div class="content" style="margin-top: 40px;">
    <div class="card">
        <h2>Contact Us</h2>
        <p><strong>Studio:</strong> 1024 NW Flanders St, Portland, OR 97209<br>
        <strong>Phone:</strong> (503) 555-0166<br>
        <strong>Studio hours:</strong> Monday through Friday, 9 a.m. to 6 p.m.</p>
        <br>
        <p>For project inquiries, please call the studio or use the contact form. We respond within two business days.</p>
    </div>
</div>
""")


# Robots.txt - the discovery hint for the staff portal

@app.route("/robots.txt")
def robots():
    return """User-agent: *
Disallow: /staff/
Disallow: /api/
Disallow: /old-cms/
""", 200, {"Content-Type": "text/plain"}


# Decoy / red herring routes

@app.route("/api/")
def api_root():
    return '{"error":"unauthorized","message":"This API requires a Kestrel staff bearer token."}', 401, {"Content-Type": "application/json"}


@app.route("/api/v1/health")
def api_v1_health():
    return '{"status":"ok","service":"kestrel-cms","version":"2.1.7"}', 200, {"Content-Type": "application/json"}


@app.route("/old-cms/")
def old_cms():
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
<head><meta charset="UTF-8"><title>Kestrel Staff</title>{STYLE}</head>
<body style="background:#1f2933;">
<div class="login-container">
    <div class="login-box">
        <h2>Kestrel Staff Login</h2>
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
        resp.set_cookie("kestrel_session", "authenticated_staff_v1")
        return resp
    return redirect("/staff/?error=1")


@app.route("/staff/dashboard")
def staff_dashboard():
    if request.cookies.get("kestrel_session") != "authenticated_staff_v1":
        return redirect("/staff/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Staff Dashboard - Kestrel</title>{STYLE}</head>
<body>
<div class="dash-header">
    <h1>Kestrel <span>Staff Dashboard</span></h1>
</div>
<div class="dash-body">
    <div class="card">
        <h2>System Overview</h2>
        <table>
            <tr><th>Component</th><th>Status</th><th>Detail</th></tr>
            <tr><td>Project CMS</td><td><span class="badge badge-green">Online</span></td><td>v2.1.7 (legacy)</td></tr>
            <tr><td>Newforma Sync</td><td><span class="badge badge-red">Disabled</span></td><td>Decommissioned 2025-03</td></tr>
            <tr><td>Engagement Token (1 of 3)</td><td><span class="badge badge-yellow">Active</span></td><td><code>{WEB_TOKEN}</code></td></tr>
            <tr><td>SMB Integration</td><td><span class="badge badge-green">Connected</span></td><td>kestrel-fs01</td></tr>
        </table>
    </div>
    <div class="card">
        <h2>Active Projects (sample)</h2>
        <table>
            <tr><th>Number</th><th>Project</th><th>Lead</th><th>Phase</th></tr>
            <tr><td>25-009</td><td>Albina Mixed Use Phase I</td><td>Daniel Okonkwo</td><td>Construction</td></tr>
            <tr><td>25-019</td><td>Riverplace Marina Office</td><td>Priya Ramaswamy</td><td>Closeout</td></tr>
            <tr><td>25-024</td><td>Holladay Park Daycare</td><td>Hana Sato</td><td>CD</td></tr>
            <tr><td>25-031</td><td>Tabor Heights Custom Residence</td><td>Theo Lindqvist</td><td>DD</td></tr>
            <tr><td>25-037</td><td>Sellwood Cafe Buildout II</td><td>Jules Bertrand</td><td>SD</td></tr>
        </table>
        <p style="color:#7a7066; font-size:0.85em; margin-top:12px;">Active project files live in Newforma. This page renders sample placeholders only.</p>
    </div>
    <div class="card">
        <h2>Application Configuration</h2>
        <p style="color:#7a7066; font-size:0.9em;">Read-only view of the running configuration.</p>
        <div class="config-block">APP_ENV=production
APP_VERSION=2.1.7
APP_OWNER=Kestrel Architecture Studio
DB_DRIVER=sqlite
DB_PATH=/var/lib/kestrel/cms.db
SMB_HOST=kestrel-fs01
SMB_BACKUP_USER=studio_archivist
LOG_LEVEL=info
DECOMMISSION_TARGET=2025-12-31</div>
        <p style="color:#b34d3f; font-size:0.8em; margin-top:10px;">
            &#9888; Project CMS was scheduled for decommission in 2025. See ticket queue for status.
        </p>
    </div>
</div>
{FOOTER}
</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
