"""Metro Transit Authority. Public REST API (broken access controls)"""

from flask import Flask, jsonify, request

app = Flask(__name__)

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f5f7fa; color: #333; }
    .nav { background: #1a3a5c; padding: 15px 30px; display: flex; align-items: center; gap: 25px; }
    .nav .brand { color: #fff; font-weight: bold; font-size: 1.15em; margin-right: auto;
                  text-decoration: none; }
    .nav .badge { background: #2e7d32; color: #fff; font-size: 0.65em; padding: 2px 8px;
                  border-radius: 4px; margin-left: 8px; vertical-align: middle; }
    .nav a { color: #90caf9; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #fff; }
    .hero { background: linear-gradient(135deg, #1a3a5c 0%, #0d2240 100%);
            padding: 60px 30px; text-align: center; border-bottom: 3px solid #42a5f5; }
    .hero h1 { color: #fff; font-size: 2.2em; margin-bottom: 10px; }
    .hero p { color: #90caf9; font-size: 1.1em; }
    .content { max-width: 960px; margin: 30px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 8px; padding: 25px; margin: 15px 0;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    .card h2 { color: #1a3a5c; margin-bottom: 12px; font-size: 1.15em; }
    .card p { line-height: 1.6; color: #555; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }
    .stat { text-align: center; padding: 20px; }
    .stat .number { color: #1a3a5c; font-size: 2.2em; font-weight: bold; }
    .stat .label { color: #888; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }
    a { color: #1565c0; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code { background: #e8eef5; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; color: #1a3a5c; }
    .endpoint { background: #f8f9fb; border: 1px solid #e0e5ec; border-radius: 6px; padding: 12px 15px;
                margin: 8px 0; font-family: monospace; font-size: 0.9em; }
    .method { display: inline-block; font-weight: bold; color: #2e7d32; margin-right: 8px; }
    .footer { text-align: center; padding: 25px; color: #999; font-size: 0.8em;
              border-top: 1px solid #e0e5ec; margin-top: 40px; }
</style>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Metro Transit Authority</title>{STYLE}</head>
<body>
<nav class="nav">
    <a href="/" class="brand">Metro Transit Authority<span class="badge">API</span></a>
    <a href="/">Home</a>
    <a href="/developer">Developers</a>
    <a href="/api/docs">API Docs</a>
</nav>
<div class="hero">
    <h1>Metro Transit Authority</h1>
    <p>Public Transit API &bull; Real-Time Arrivals &bull; Route Information</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card stat">
            <div class="number">5</div>
            <div class="label">Active Routes</div>
        </div>
        <div class="card stat">
            <div class="number">142K</div>
            <div class="label">Daily Riders</div>
        </div>
        <div class="card stat">
            <div class="number">99.1%%</div>
            <div class="label">On-Time Performance</div>
        </div>
    </div>

    <div class="card">
        <h2>Developer API</h2>
        <p>Access real-time transit data through our public REST API. Route schedules,
        live arrival estimates, and service alerts are available to all developers
        at no cost.</p>
        <br>
        <div class="endpoint"><span class="method">GET</span> /api/routes &mdash; List all transit routes</div>
        <div class="endpoint"><span class="method">GET</span> /api/schedules &mdash; Current schedules</div>
        <div class="endpoint"><span class="method">GET</span> /api/arrivals &mdash; Real-time arrival estimates</div>
        <div class="endpoint"><span class="method">GET</span> /api/alerts &mdash; Service alerts</div>
        <br>
        <p>Full documentation: <a href="/api/docs">/api/docs</a></p>
    </div>

    <div class="card">
        <h2>About MTA</h2>
        <p>The Metro Transit Authority serves the greater metropolitan area with bus, rail,
        and ferry service. Established in 1967, we transport over 142,000 riders daily across
        five routes spanning 85 miles of service area. Our mission is safe, reliable, and
        accessible public transit for all.</p>
    </div>
</div>
<div class="footer">
    &copy; 2024 Metro Transit Authority. A public service agency.<br>
    <a href="/api/docs">API Documentation</a> &bull;
    Contact: api-support@metro-transit.gov &bull; (206) 555-0100
</div>
</body></html>"""


@app.route("/developer")
def developer():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Developers - Metro Transit</title>{STYLE}</head>
<body>
<nav class="nav">
    <a href="/" class="brand">Metro Transit Authority<span class="badge">API</span></a>
    <a href="/">Home</a>
    <a href="/developer">Developers</a>
    <a href="/api/docs">API Docs</a>
</nav>
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Developer Resources</h2>
        <p>Our public API provides free access to transit data. No API key required for
        public endpoints. Rate limited to 100 requests per minute per IP.</p>
        <br>
        <p><strong>Base URL:</strong> <code>/api</code><br>
        <strong>Format:</strong> JSON<br>
        <strong>Rate Limit:</strong> 100 req/min per IP<br>
        <strong>Support:</strong> api-support@metro-transit.gov</p>
    </div>
</div>
<div class="footer">
    &copy; 2024 Metro Transit Authority.<br>
    <a href="/api/docs">API Documentation</a>
</div>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
# Public endpoints (documented, intended for external developers)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/docs")
def docs():
    return jsonify({
        "api": "Metro Transit Authority. Public API",
        "version": "2.3.1",
        "base_url": "/api",
        "endpoints": {
            "GET /api/routes": "List all transit routes",
            "GET /api/routes/<id>": "Get route details",
            "GET /api/schedules": "Current schedules",
            "GET /api/arrivals": "Real-time arrival estimates",
            "GET /api/alerts": "Service alerts and disruptions"
        },
        "authentication": "Public endpoints require no authentication.",
        "rate_limit": "100 requests/minute per IP",
        "contact": "api-support@metro-transit.gov"
    })


@app.route("/api/routes")
def routes():
    return jsonify({"routes": [
        {"id": 1, "name": "Line 1 - Downtown Express", "type": "bus", "status": "active"},
        {"id": 2, "name": "Line 2 - University Connector", "type": "bus", "status": "active"},
        {"id": 3, "name": "Blue Line - Airport Link", "type": "rail", "status": "active"},
        {"id": 4, "name": "Line 4 - Waterfront Loop", "type": "ferry", "status": "suspended"},
        {"id": 5, "name": "Red Line - East Side", "type": "rail", "status": "active"},
    ]})


@app.route("/api/schedules")
def schedules():
    return jsonify({"schedules": [
        {"route_id": 1, "first_departure": "05:30", "last_departure": "23:45", "frequency_min": 10},
        {"route_id": 2, "first_departure": "06:00", "last_departure": "22:00", "frequency_min": 15},
        {"route_id": 3, "first_departure": "04:45", "last_departure": "00:30", "frequency_min": 12},
    ]})


@app.route("/api/arrivals")
def arrivals():
    return jsonify({"arrivals": [
        {"route_id": 1, "stop": "3rd & Pike", "eta_min": 3},
        {"route_id": 3, "stop": "SeaTac Terminal", "eta_min": 8},
        {"route_id": 5, "stop": "Bellevue TC", "eta_min": 12},
    ]})


@app.route("/api/alerts")
def alerts():
    return jsonify({"alerts": [
        {"id": "A-2024-0891", "route_id": 4, "type": "suspension",
         "message": "Line 4 suspended due to dock maintenance. Expected resumption: Oct 15."}
    ]})


# ═══════════════════════════════════════════════════════════════════════
# Admin endpoints (SHOULD require auth, but access control is broken)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/admin/users")
def admin_users():
    # BUG: No authentication check. anyone can access admin data
    return jsonify({
        "admin_panel": "MTA Internal User Management",
        "assessment_token": "4p1",
        "users": [
            {"id": 1, "username": "lpark", "role": "admin", "email": "lisa.park@metro-transit.gov",
             "last_login": "2024-09-15T08:22:00Z"},
            {"id": 2, "username": "jnguyen", "role": "operator", "email": "james.nguyen@metro-transit.gov",
             "last_login": "2024-09-15T06:45:00Z"},
            {"id": 3, "username": "api_readonly", "role": "service", "email": "noreply@metro-transit.gov",
             "api_key": "mta_pk_live_8f2a1b9c4d7e3f6a"},
            {"id": 4, "username": "kthompson", "role": "analyst", "email": "karen.thompson@metro-transit.gov",
             "last_login": "2024-09-14T16:30:00Z"},
        ]
    })


@app.route("/api/admin/config")
def admin_config():
    return jsonify({"error": "unauthorized", "message": "Admin API key required"}), 401


# ═══════════════════════════════════════════════════════════════════════
# Debug endpoint (should be disabled in production)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/debug")
def debug():
    return jsonify({
        "debug_mode": True,
        "debug_token": "br0k3n_acc3ss",
        "environment": "production",
        "database": "postgresql://mta_app:Tr4ns1t_DB!@db.internal:5432/mta_prod",
        "redis": "redis://cache.internal:6379/0",
        "flask_secret": "super-secret-key-change-in-prod",
        "build": "2024-09-15T02:30:00Z",
        "warning": "DEBUG ENDPOINT. DISABLE BEFORE PRODUCTION DEPLOYMENT"
    })


@app.route("/api/internal")
def internal():
    return jsonify({"error": "forbidden", "message": "Internal network only"}), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
