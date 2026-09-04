"""CloudPing Diagnostics. Network Ping Tool (vulnerable to command injection)"""

from flask import Flask, request
import subprocess

app = Flask(__name__)

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #1a202c; color: #e2e8f0; }
    .nav { background: #171923; padding: 15px 30px; display: flex; align-items: center; gap: 25px;
           border-bottom: 1px solid #2d3748; }
    .nav .brand { color: #4299e1; font-weight: bold; font-size: 1.15em; margin-right: auto;
                  text-decoration: none; letter-spacing: 1px; }
    .nav a { color: #718096; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #4299e1; }
    .hero { background: linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #1a365d 100%);
            padding: 50px 30px; text-align: center; border-bottom: 2px solid #4299e1; }
    .hero h1 { color: #4299e1; font-size: 2.2em; margin-bottom: 10px; }
    .hero p { color: #718096; font-size: 1.05em; }
    .content { max-width: 800px; margin: 30px auto; padding: 0 20px; }
    .card { background: #2d3748; border-radius: 8px; padding: 30px; margin: 20px 0;
            border: 1px solid #4a5568; }
    .card h2 { color: #e2e8f0; margin-bottom: 12px; }
    .card p { line-height: 1.6; color: #a0aec0; }
    input[type=text] { width: 70%%; padding: 10px; border: 1px solid #4a5568; background: #1a202c;
                       color: #e2e8f0; border-radius: 4px; font-size: 1em; }
    button { padding: 10px 25px; background: #4299e1; color: #fff; border: none; border-radius: 4px;
             font-size: 1em; cursor: pointer; margin-left: 10px; font-weight: bold; }
    button:hover { background: #3182ce; }
    pre { background: #1a202c; border: 1px solid #4a5568; padding: 15px; border-radius: 4px;
          overflow-x: auto; margin-top: 15px; color: #68d391; font-size: 0.9em; }
    .note { color: #718096; font-size: 0.85em; margin-top: 10px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; }
    .stat { text-align: center; padding: 20px; }
    .stat .number { color: #4299e1; font-size: 1.8em; font-weight: bold; }
    .stat .label { color: #718096; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;
                   margin-top: 5px; }
    .footer { text-align: center; padding: 25px; color: #4a5568; font-size: 0.8em;
              border-top: 1px solid #2d3748; margin-top: 40px; }
    .footer a { color: #4299e1; text-decoration: none; }
    a { color: #4299e1; text-decoration: none; }
    a:hover { text-decoration: underline; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">CloudPing</a>
    <a href="/">Home</a>
    <a href="/ping-tool">Ping Tool</a>
    <a href="/about">About</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 CloudPing Diagnostics, Inc. All rights reserved.<br>
    <a href="/about">About</a> &bull; <a href="/privacy">Privacy</a> &bull;
    <a href="/terms">Terms</a><br>
    San Francisco, CA &bull; Ashburn, VA &bull; Frankfurt, DE
</div>"""


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>CloudPing Diagnostics</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>CloudPing Diagnostics</h1>
    <p>Network connectivity testing &bull; Latency monitoring &bull; Uptime verification</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card stat">
            <div class="number">12</div>
            <div class="label">Global PoPs</div>
        </div>
        <div class="card stat">
            <div class="number">4.2M</div>
            <div class="label">Tests Run</div>
        </div>
        <div class="card stat">
            <div class="number">99.9%%</div>
            <div class="label">Uptime SLA</div>
        </div>
    </div>

    <div class="card">
        <h2>Network Connectivity Test</h2>
        <p>Enter a hostname or IP address to test connectivity from our server.</p>
        <form method="POST" action="/ping" style="margin-top:15px;">
            <input type="text" name="host" placeholder="Enter hostname or IP (e.g., 8.8.8.8)" required>
            <button type="submit">Ping</button>
        </form>
        <p class="note">Sends 2 ICMP echo requests to the specified host from our US-West PoP.</p>
    </div>

    <div class="card">
        <h2>Why CloudPing?</h2>
        <p>CloudPing Diagnostics provides network testing tools for DevOps teams, SREs, and
        network engineers. Test connectivity from 12 global points of presence, monitor latency
        trends, and set up automated uptime alerts. all from a single dashboard.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - CloudPing</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>About CloudPing Diagnostics</h2>
        <p>Founded in 2020, CloudPing provides simple, reliable network diagnostic tools
        for infrastructure teams. What started as an internal tool at a hosting company
        now serves over 15,000 users worldwide.</p>
        <br>
        <p><strong>Headquarters:</strong> 155 5th St, Suite 400, San Francisco, CA 94103<br>
        <strong>Email:</strong> hello@cloudping.io<br>
        <strong>Support:</strong> support@cloudping.io</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/ping-tool")
def ping_tool():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Ping Tool - CloudPing</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Network Connectivity Test</h2>
        <p>Enter a hostname or IP address to test connectivity from our server.</p>
        <form method="POST" action="/ping" style="margin-top:15px;">
            <input type="text" name="host" placeholder="Enter hostname or IP (e.g., 8.8.8.8)" required>
            <button type="submit">Ping</button>
        </form>
        <p class="note">Sends 2 ICMP echo requests to the specified host.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/ping", methods=["POST"])
def ping():
    host = request.form.get("host", "")
    if not host:
        return "Missing host parameter", 400

    # VULNERABLE: User input passed directly to shell command
    try:
        result = subprocess.run(
            f"ping -c 2 -W 3 {host}",
            shell=True,  # shell=True enables command injection
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        output = "Request timed out."
    except Exception as e:
        output = f"Error: {str(e)}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Ping Results - CloudPing</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Results for: {host}</h2>
        <pre>{output}</pre>
        <p style="margin-top:15px;"><a href="/">Run another test</a></p>
    </div>
</div>
{FOOTER}
</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
