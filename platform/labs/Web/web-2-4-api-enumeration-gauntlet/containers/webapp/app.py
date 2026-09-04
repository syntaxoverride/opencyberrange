"""Stonebridge Capital. Portfolio Management REST API (versioned endpoint leak)"""

from flask import Flask, jsonify, request

app = Flask(__name__)

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f5f7fa; color: #333; }
    .nav { background: #1b2a4a; padding: 15px 30px; display: flex; align-items: center; gap: 25px; }
    .nav .brand { color: #fff; font-weight: bold; font-size: 1.15em; margin-right: auto;
                  text-decoration: none; }
    .nav .badge { background: #c9962b; color: #fff; font-size: 0.65em; padding: 2px 8px;
                  border-radius: 4px; margin-left: 8px; vertical-align: middle; }
    .nav a { color: #8bacd4; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #fff; }
    .hero { background: linear-gradient(135deg, #1b2a4a 0%, #0f1a30 100%);
            padding: 60px 30px; text-align: center; border-bottom: 3px solid #c9962b; }
    .hero h1 { color: #fff; font-size: 2.2em; margin-bottom: 10px; }
    .hero p { color: #8bacd4; font-size: 1.1em; }
    .content { max-width: 960px; margin: 30px auto; padding: 0 20px; }
    .card { background: #fff; border-radius: 8px; padding: 25px; margin: 15px 0;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    .card h2 { color: #1b2a4a; margin-bottom: 12px; font-size: 1.15em; }
    .card p { line-height: 1.6; color: #555; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }
    .stat { text-align: center; padding: 20px; }
    .stat .number { color: #1b2a4a; font-size: 2.2em; font-weight: bold; }
    .stat .label { color: #888; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }
    a { color: #1b5e9e; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code { background: #e8eef5; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; color: #1b2a4a; }
    .endpoint { background: #f8f9fb; border: 1px solid #e0e5ec; border-radius: 6px; padding: 12px 15px;
                margin: 8px 0; font-family: monospace; font-size: 0.9em; }
    .method { display: inline-block; font-weight: bold; color: #2e7d32; margin-right: 8px; }
    .locked { color: #b71c1c; }
    .footer { text-align: center; padding: 25px; color: #999; font-size: 0.8em;
              border-top: 1px solid #e0e5ec; margin-top: 40px; }
</style>"""


# ═══════════════════════════════════════════════════════════════════════
# Landing page. only documents v1 endpoints
# ═══════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Stonebridge Capital. API</title>{STYLE}</head>
<body>
<nav class="nav">
    <a href="/" class="brand">Stonebridge Capital<span class="badge">API</span></a>
    <a href="/">Home</a>
    <a href="/developers">Developers</a>
</nav>
<div class="hero">
    <h1>Stonebridge Capital</h1>
    <p>Portfolio Management API &bull; Institutional-Grade Infrastructure</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card stat">
            <div class="number">$4.2B</div>
            <div class="label">Assets Under Management</div>
        </div>
        <div class="card stat">
            <div class="number">340</div>
            <div class="label">Portfolio Companies</div>
        </div>
        <div class="card stat">
            <div class="number">99.97%%</div>
            <div class="label">API Uptime</div>
        </div>
    </div>

    <div class="card">
        <h2>API v1. Production Endpoints</h2>
        <p>All v1 endpoints require a valid API key passed via the
        <code>X-API-Key</code> header. Contact your account manager
        to request access.</p>
        <br>
        <div class="endpoint"><span class="method locked">GET</span> /api/v1/users &mdash; List authorized users <em>(requires API key)</em></div>
        <div class="endpoint"><span class="method locked">GET</span> /api/v1/portfolios &mdash; Portfolio summaries <em>(requires API key)</em></div>
        <div class="endpoint"><span class="method locked">GET</span> /api/v1/transactions &mdash; Recent transactions <em>(requires API key)</em></div>
        <br>
        <p><strong>Base URL:</strong> <code>/api/v1</code><br>
        <strong>Auth:</strong> API key required for all endpoints<br>
        <strong>Rate Limit:</strong> 60 req/min per key</p>
    </div>

    <div class="card">
        <h2>About Stonebridge Capital</h2>
        <p>Founded in 2006, Stonebridge Capital is a Chicago-based private equity firm
        specializing in mid-market acquisitions across technology, healthcare, and
        financial services. Our API provides programmatic access to portfolio data
        for authorized institutional partners.</p>
    </div>
</div>
<div class="footer">
    &copy; 2024 Stonebridge Capital, LP. All rights reserved.<br>
    <a href="/developers">Developer Portal</a> &bull;
    Contact: api-support@stonebridgecap.com &bull; (312) 555-0180
</div>
</body></html>"""


@app.route("/developers")
def developers():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Developers. Stonebridge Capital</title>{STYLE}</head>
<body>
<nav class="nav">
    <a href="/" class="brand">Stonebridge Capital<span class="badge">API</span></a>
    <a href="/">Home</a>
    <a href="/developers">Developers</a>
</nav>
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Developer Resources</h2>
        <p>The Stonebridge Capital API (v1) provides secure access to portfolio data
        for authorized partners. All requests must include a valid API key.</p>
        <br>
        <p><strong>Base URL:</strong> <code>/api/v1</code><br>
        <strong>Format:</strong> JSON<br>
        <strong>Authentication:</strong> <code>X-API-Key</code> header (required)<br>
        <strong>Rate Limit:</strong> 60 req/min per key<br>
        <strong>Support:</strong> api-support@stonebridgecap.com</p>
    </div>
    <div class="card">
        <h2>Requesting Access</h2>
        <p>API keys are issued to verified institutional partners only. Contact your
        Stonebridge account manager or email api-support@stonebridgecap.com with your
        organization details and intended use case.</p>
    </div>
</div>
<div class="footer">
    &copy; 2024 Stonebridge Capital, LP.<br>
    <a href="/">Home</a>
</div>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
# v1 API. all endpoints return 401 (locked down)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/v1/users")
def v1_users():
    return jsonify({"error": "unauthorized", "message": "API key required. Include a valid X-API-Key header."}), 401


@app.route("/api/v1/portfolios")
def v1_portfolios():
    return jsonify({"error": "unauthorized", "message": "API key required. Include a valid X-API-Key header."}), 401


@app.route("/api/v1/transactions")
def v1_transactions():
    return jsonify({"error": "unauthorized", "message": "API key required. Include a valid X-API-Key header."}), 401


# ═══════════════════════════════════════════════════════════════════════
# v2 API. development preview (NOT documented, missing auth checks)
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/v2/users")
def v2_users():
    # BUG: No authentication required. v2 was intended for internal use only
    return jsonify({
        "api_version": "v2-dev",
        "users": [
            {
                "id": 1,
                "username": "mwebb",
                "full_name": "Marcus Webb",
                "role": "cto",
                "email": "marcus.webb@stonebridgecap.com",
                "last_login": "2024-10-12T09:15:00Z"
            },
            {
                "id": 2,
                "username": "jchen",
                "full_name": "Jennifer Chen",
                "role": "portfolio_manager",
                "email": "jennifer.chen@stonebridgecap.com",
                "last_login": "2024-10-12T08:42:00Z"
            },
            {
                "id": 3,
                "username": "svc_internal",
                "full_name": "Internal Service Account",
                "role": "service",
                "email": "noreply@stonebridgecap.com",
                "auth_token": "SB_tk_4p1_v3rs10n",
                "last_login": "2024-10-12T00:00:00Z"
            },
            {
                "id": 4,
                "username": "rpatterson",
                "full_name": "Robert Patterson",
                "role": "analyst",
                "email": "robert.patterson@stonebridgecap.com",
                "last_login": "2024-10-11T17:30:00Z"
            }
        ]
    })


@app.route("/api/v2/admin/config")
def v2_admin_config():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != "Bearer SB_tk_4p1_v3rs10n":
        return jsonify({
            "error": "forbidden",
            "message": "Valid Bearer token required."
        }), 403

    return jsonify({
        "api_version": "v2-dev",
        "environment": "staging",
        "database": {
            "host": "sb-db",
            "port": 3306,
            "db_name": "stonebridge",
            "db_user": "sb_app",
            "db_pass": "St0n3br1dg3_DB#",
            "note": "Backend MySQL. resolve via internal hostname or scan the subnet"
        },
        "feature_flags": {
            "v2_public_access": True,
            "audit_logging": False,
            "rate_limiting": False
        },
        "warning": "v2 admin config. DO NOT expose in production"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
