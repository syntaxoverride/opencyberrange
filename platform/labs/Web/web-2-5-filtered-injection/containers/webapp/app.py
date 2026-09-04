"""TrueNorth Hosting. DNS Lookup Tool (vulnerable to newline injection)"""

from flask import Flask, request
import subprocess

app = Flask(__name__)

STYLE = """<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1923; color: #e2e8f0; }
    .nav { background: #0a1017; padding: 15px 30px; display: flex; align-items: center; gap: 25px;
           border-bottom: 1px solid #1e3a5f; }
    .nav .brand { color: #38bdf8; font-weight: bold; font-size: 1.15em; margin-right: auto;
                  text-decoration: none; letter-spacing: 1px; }
    .nav a { color: #64748b; text-decoration: none; font-size: 0.9em; }
    .nav a:hover { color: #38bdf8; }
    .hero { background: linear-gradient(135deg, #0f1923 0%, #1e3a5f 50%, #0c4a6e 100%);
            padding: 50px 30px; text-align: center; border-bottom: 2px solid #38bdf8; }
    .hero h1 { color: #38bdf8; font-size: 2.2em; margin-bottom: 10px; }
    .hero p { color: #64748b; font-size: 1.05em; }
    .content { max-width: 800px; margin: 30px auto; padding: 0 20px; }
    .card { background: #1e293b; border-radius: 8px; padding: 30px; margin: 20px 0;
            border: 1px solid #334155; }
    .card h2 { color: #e2e8f0; margin-bottom: 12px; }
    .card p { line-height: 1.6; color: #94a3b8; }
    input[type=text] { width: 70%%; padding: 10px; border: 1px solid #334155; background: #0f1923;
                       color: #e2e8f0; border-radius: 4px; font-size: 1em; }
    button { padding: 10px 25px; background: #0284c7; color: #fff; border: none; border-radius: 4px;
             font-size: 1em; cursor: pointer; margin-left: 10px; font-weight: bold; }
    button:hover { background: #0369a1; }
    pre { background: #0f1923; border: 1px solid #334155; padding: 15px; border-radius: 4px;
          overflow-x: auto; margin-top: 15px; color: #4ade80; font-size: 0.9em;
          white-space: pre-wrap; word-wrap: break-word; }
    .note { color: #64748b; font-size: 0.85em; margin-top: 10px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; }
    .stat { text-align: center; padding: 20px; }
    .stat .number { color: #38bdf8; font-size: 1.8em; font-weight: bold; }
    .stat .label { color: #64748b; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;
                   margin-top: 5px; }
    .footer { text-align: center; padding: 25px; color: #334155; font-size: 0.8em;
              border-top: 1px solid #1e293b; margin-top: 40px; }
    .footer a { color: #38bdf8; text-decoration: none; }
    a { color: #38bdf8; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .filter-badge { display: inline-block; background: #166534; color: #4ade80; padding: 3px 10px;
                    border-radius: 12px; font-size: 0.75em; margin-left: 10px; }
</style>"""

NAV = """<nav class="nav">
    <a href="/" class="brand">TrueNorth Hosting</a>
    <a href="/">Home</a>
    <a href="/lookup-tool">DNS Lookup</a>
    <a href="/about">About</a>
</nav>"""

FOOTER = """<div class="footer">
    &copy; 2024 TrueNorth Hosting, LLC. All rights reserved.<br>
    <a href="/about">About</a> &bull; <a href="/privacy">Privacy</a> &bull;
    <a href="/terms">Terms</a><br>
    Toronto, ON &bull; Montreal, QC &bull; Vancouver, BC
</div>"""


def sanitize_input(user_input):
    """Strip dangerous shell metacharacters from user input."""
    dangerous = [";", "|", "&", "&&", "||"]
    cleaned = user_input
    for char in dangerous:
        cleaned = cleaned.replace(char, "")
    return cleaned


@app.route("/")
def index():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>TrueNorth Hosting</title>{STYLE}</head>
<body>
{NAV}
<div class="hero">
    <h1>TrueNorth Hosting</h1>
    <p>Managed DNS &bull; Web Hosting &bull; Domain Services</p>
</div>
<div class="content">
    <div class="grid">
        <div class="card stat">
            <div class="number">8,200+</div>
            <div class="label">Domains Managed</div>
        </div>
        <div class="card stat">
            <div class="number">99.99%%</div>
            <div class="label">DNS Uptime</div>
        </div>
        <div class="card stat">
            <div class="number">3</div>
            <div class="label">Data Centers</div>
        </div>
    </div>

    <div class="card">
        <h2>DNS Lookup Tool <span class="filter-badge">Input Sanitized</span></h2>
        <p>Check DNS records for any domain using our server-side lookup tool.
        Enter a domain name below to run an nslookup query.</p>
        <form method="POST" action="/lookup" style="margin-top:15px;">
            <input type="text" name="domain" placeholder="Enter domain (e.g., example.com)" required>
            <button type="submit">Lookup</button>
        </form>
        <p class="note">Runs nslookup from our Toronto data center. Input is filtered for security.</p>
    </div>

    <div class="card">
        <h2>Why TrueNorth?</h2>
        <p>TrueNorth Hosting provides reliable, Canadian-based hosting and DNS management
        for businesses of all sizes. With data centers in Toronto, Montreal, and Vancouver,
        we offer low-latency services across North America with full PIPEDA compliance.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/about")
def about():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>About - TrueNorth Hosting</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>About TrueNorth Hosting</h2>
        <p>Founded in 2018, TrueNorth Hosting is a Canadian web hosting and DNS management
        company serving over 8,000 customers. We specialize in reliable, privacy-focused
        hosting with all infrastructure located in Canada.</p>
        <br>
        <p><strong>Headquarters:</strong> 200 Bay St, Suite 1500, Toronto, ON M5J 2J1<br>
        <strong>Email:</strong> info@truenorthhosting.ca<br>
        <strong>Support:</strong> support@truenorthhosting.ca</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/lookup-tool")
def lookup_tool():
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>DNS Lookup - TrueNorth Hosting</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>DNS Lookup Tool <span class="filter-badge">Input Sanitized</span></h2>
        <p>Enter a domain name to perform a DNS lookup from our server.</p>
        <form method="POST" action="/lookup" style="margin-top:15px;">
            <input type="text" name="domain" placeholder="Enter domain (e.g., example.com)" required>
            <button type="submit">Lookup</button>
        </form>
        <p class="note">Input is sanitized to prevent abuse. Dangerous characters are stripped.</p>
    </div>
</div>
{FOOTER}
</body></html>"""


@app.route("/lookup", methods=["POST"])
def lookup():
    domain = request.form.get("domain", "")
    if not domain:
        return "Missing domain parameter", 400

    # Sanitize input. strip dangerous shell metacharacters
    cleaned = sanitize_input(domain)

    # VULNERABLE: newline characters (%0a) are not filtered
    try:
        result = subprocess.run(
            f"nslookup {cleaned}",
            shell=True,
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
<head><meta charset="UTF-8"><title>Lookup Results - TrueNorth Hosting</title>{STYLE}</head>
<body>
{NAV}
<div class="content" style="margin-top:40px;">
    <div class="card">
        <h2>Results for: {cleaned}</h2>
        <pre>{output}</pre>
        <p style="margin-top:15px;"><a href="/lookup-tool">Run another lookup</a></p>
    </div>
</div>
{FOOTER}
</body></html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
