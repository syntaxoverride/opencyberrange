#!/usr/bin/env python3
"""Titan Global Industries. Corporate Product Portal (server-alpha)."""

import sqlite3
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
DB_PATH = "/app/titan.db"


def init_db():
    """Initialize the SQLite database with products and secrets tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            price REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY,
            flag_value TEXT
        )
    """)
    # Seed products
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            ("TitanShield Pro", "Enterprise firewall appliance", 4999.99),
            ("TitanVault", "Encrypted storage solution", 2499.99),
            ("TitanLink Mesh", "Industrial mesh networking kit", 1299.99),
            ("TitanWatch SIEM", "Security monitoring platform", 8999.99),
            ("TitanGuard EDR", "Endpoint detection and response", 3499.99),
        ]
        c.executemany("INSERT INTO products (name, description, price) VALUES (?, ?, ?)", products)
    # Seed secret
    c.execute("SELECT COUNT(*) FROM secrets")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO secrets (flag_value) VALUES (?)", ("t1t4n",))
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return """<!DOCTYPE html>
<html>
<head><title>Titan Global Industries. Product Portal</title></head>
<body>
<h1>Titan Global Industries</h1>
<h2>Product Search Portal</h2>
<form action="/search" method="GET">
    <input type="text" name="q" placeholder="Search products...">
    <button type="submit">Search</button>
</form>
<p>Browse our enterprise security product catalog.</p>
<hr>
<p><small>&copy; 2024 Titan Global Industries. All rights reserved.</small></p>
</body>
</html>"""


@app.route("/search")
def search():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Please provide a search query parameter 'q'"}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Intentionally vulnerable to SQL injection
    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
    try:
        c.execute(sql)
        rows = c.fetchall()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500
    conn.close()
    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
        })
    return jsonify({"query": query, "results": results})


@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nDisallow: /api/internal\n",
        mimetype="text/plain",
    )


@app.route("/api/internal")
def internal():
    return jsonify({"error": "Forbidden. internal API only"}), 403


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
