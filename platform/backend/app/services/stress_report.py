"""
Stress Test PDF Report Generator

Generates a multi-page PDF with color-coded health scoring,
bar charts, and detailed endpoint tables.

Uses matplotlib for charts and fpdf2 for PDF composition.
Professional light theme designed for printing.
"""

import io
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from fpdf import FPDF


# ── Color constants (light/print-friendly theme) ────────────────────────
GREEN = (22, 163, 74)        # #16a34a  - professional green
YELLOW = (202, 138, 4)       # #ca8a04  - darker gold (readable on white)
RED = (220, 38, 38)          # #dc2626  - professional red
PAGE_BG = (255, 255, 255)    # white
CARD_BG = (245, 247, 250)    # #f5f7fa  - light gray card
TEXT_PRIMARY = (30, 41, 59)   # #1e293b  - dark slate
TEXT_MUTED = (100, 116, 139)  # #64748b  - medium gray
WHITE = (255, 255, 255)
TABLE_HEADER_BG = (37, 99, 235)   # #2563eb  - professional blue
TABLE_ALT_ROW = (248, 250, 252)   # #f8fafc  - very light gray

# Matplotlib light theme colors
MPL_BG = "#ffffff"
MPL_CARD = "#f5f7fa"
MPL_TEXT = "#1e293b"
MPL_MUTED = "#64748b"
MPL_GREEN = "#16a34a"
MPL_YELLOW = "#ca8a04"
MPL_RED = "#dc2626"
MPL_BLUE = "#2563eb"
MPL_GRID = "#e2e8f0"


# ── Scoring logic ────────────────────────────────────────────────────────

def _latency_color(p95, is_docker=False):
    """Return (r,g,b) for a p95 latency value."""
    if is_docker:
        if p95 < 5.0:
            return GREEN
        elif p95 < 10.0:
            return YELLOW
        return RED
    else:
        if p95 < 0.5:
            return GREEN
        elif p95 < 2.0:
            return YELLOW
        return RED


def _latency_label(p95, is_docker=False):
    if is_docker:
        if p95 < 5.0:
            return "green"
        elif p95 < 10.0:
            return "yellow"
        return "red"
    else:
        if p95 < 0.5:
            return "green"
        elif p95 < 2.0:
            return "yellow"
        return "red"


def _compute_health_checks(data):
    """Compute the 6 health checks from stress test results."""
    endpoints = data.get("endpoints", [])
    total_calls = data.get("total_calls", 0)
    total_errors = data.get("total_errors", 0)
    error_rate = data.get("error_rate", 0)
    duration = data.get("duration_seconds", 0)
    users = data.get("users", 0)

    rps = round(total_calls / duration, 1) if duration > 0 else 0

    # 1. Latency check
    all_latency_green = True
    any_latency_red = False
    for ep in endpoints:
        is_docker = "spawn" in ep["endpoint"].lower() or "stop" in ep["endpoint"].lower()
        color = _latency_label(ep["p95"], is_docker)
        if color != "green":
            all_latency_green = False
        if color == "red":
            any_latency_red = True

    if any_latency_red:
        latency_status = "red"
        latency_text = "Some endpoints are too slow for users"
    elif not all_latency_green:
        latency_status = "yellow"
        latency_text = "Some endpoints approaching slowness threshold"
    else:
        latency_status = "green"
        latency_text = "All responses under 0.5 seconds"

    # 2. Error rate check
    if error_rate > 5:
        error_status = "red"
        error_text = f"{error_rate}% failure rate  - above 5% limit"
    elif error_rate > 1:
        error_status = "yellow"
        error_text = f"{error_rate}% failure rate  - approaching 5% limit"
    else:
        error_status = "green"
        error_text = f"{error_rate}% failure rate  - well within limits"

    # 3. Throughput
    if rps > 50:
        rps_status = "green"
        rps_text = f"{rps} requests/sec  - good capacity"
    elif rps > 20:
        rps_status = "yellow"
        rps_text = f"{rps} requests/sec  - moderate capacity"
    else:
        rps_status = "red"
        rps_text = f"{rps} requests/sec  - low capacity"

    # 4. User completion
    completed = data.get("users_completed", users)
    if completed >= users:
        user_status = "green"
        user_text = f"All {users} users completed successfully"
    elif completed / max(users, 1) > 0.9:
        user_status = "yellow"
        pct = round(completed / max(users, 1) * 100)
        user_text = f"{completed}/{users} users completed ({pct}%)"
    else:
        user_status = "red"
        pct = round(completed / max(users, 1) * 100)
        user_text = f"Only {completed}/{users} users completed ({pct}%)"

    # 5. Stability (no 500 errors)
    server_errors = 0
    for err in data.get("top_errors", []):
        if "500" in err.get("error", ""):
            server_errors += 1
    if server_errors > 0:
        stability_status = "red"
        stability_text = f"{server_errors} server crashes detected"
    elif total_errors > 0:
        stability_status = "yellow"
        stability_text = f"{total_errors} minor errors (no crashes)"
    else:
        stability_status = "green"
        stability_text = "No errors detected"

    # 6. DB pool
    db_errors = sum(1 for err in data.get("top_errors", []) if "pool" in err.get("error", "").lower() or "connection" in err.get("error", "").lower())
    if db_errors > 0:
        db_status = "red"
        db_text = "Database connection issues detected"
    else:
        db_status = "green"
        db_text = "Database connections healthy"

    checks = [
        ("Response Time", latency_status, latency_text),
        ("Error Rate", error_status, error_text),
        ("Throughput", rps_status, rps_text),
        ("User Completion", user_status, user_text),
        ("Stability", stability_status, stability_text),
        ("Database", db_status, db_text),
    ]

    # Overall scoring
    reds = sum(1 for _, s, _ in checks if s == "red")
    yellows = sum(1 for _, s, _ in checks if s == "yellow")

    if reds >= 2:
        overall = "red"
        overall_label = "CRITICAL"
    elif reds >= 1 or yellows >= 3:
        overall = "yellow"
        overall_label = "NEEDS ATTENTION"
    else:
        overall = "green"
        overall_label = "HEALTHY"

    passed = sum(1 for _, s, _ in checks if s == "green")

    return {
        "checks": checks,
        "overall": overall,
        "overall_label": overall_label,
        "passed": passed,
        "total": len(checks),
        "rps": rps,
    }


# ── Chart generators ─────────────────────────────────────────────────────

def _create_p95_bar_chart(endpoints):
    """Horizontal bar chart of response times (slowest 5%) with color-coded bars."""
    if not endpoints:
        return None

    fig, ax = plt.subplots(figsize=(7.5, max(2.5, len(endpoints) * 0.45)))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    names = [ep["endpoint"] for ep in reversed(endpoints)]
    p95s = [ep["p95"] for ep in reversed(endpoints)]

    colors = []
    for ep in reversed(endpoints):
        is_docker = "spawn" in ep["endpoint"].lower() or "stop" in ep["endpoint"].lower()
        label = _latency_label(ep["p95"], is_docker)
        colors.append({"green": MPL_GREEN, "yellow": MPL_YELLOW, "red": MPL_RED}[label])

    bars = ax.barh(range(len(names)), p95s, color=colors, height=0.6, edgecolor="none")

    # Add value labels
    for bar, val in zip(bars, p95s):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}s", va="center", ha="left", fontsize=8, color=MPL_TEXT)

    # Threshold lines
    ax.axvline(x=0.5, color=MPL_YELLOW, linestyle="--", linewidth=0.8, alpha=0.7)
    ax.axvline(x=2.0, color=MPL_RED, linestyle="--", linewidth=0.8, alpha=0.7)

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7, color=MPL_TEXT, fontfamily="monospace")
    ax.set_xlabel("Response Time (seconds)", fontsize=9, color=MPL_MUTED)
    ax.set_title("Endpoint Response Times (Slowest 5% of Requests)", fontsize=11, color=MPL_TEXT, fontweight="bold", pad=10)

    ax.tick_params(axis="x", colors=MPL_MUTED, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(MPL_GRID)
    ax.spines["left"].set_color(MPL_GRID)
    ax.grid(axis="x", color=MPL_GRID, linewidth=0.5, alpha=0.7)

    # Legend
    green_patch = mpatches.Patch(color=MPL_GREEN, label="Fast (< 0.5s)")
    yellow_patch = mpatches.Patch(color=MPL_YELLOW, label="Slow (0.5 - 2.0s)")
    red_patch = mpatches.Patch(color=MPL_RED, label="Too Slow (> 2.0s)")
    ax.legend(handles=[green_patch, yellow_patch, red_patch], loc="lower right",
              fontsize=7, facecolor=MPL_BG, edgecolor=MPL_GRID,
              labelcolor=MPL_TEXT)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _create_percentile_comparison(endpoints, users=0):
    """Grouped bar chart comparing typical, slow, and worst-case response times."""
    if not endpoints:
        return None

    fig, ax = plt.subplots(figsize=(7.5, max(2.5, len(endpoints) * 0.55)))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    names = [ep["endpoint"] for ep in reversed(endpoints)]
    p50s = [ep["p50"] for ep in reversed(endpoints)]
    p95s = [ep["p95"] for ep in reversed(endpoints)]
    p99s = [ep["p99"] for ep in reversed(endpoints)]

    y = range(len(names))
    h = 0.25

    # Calculate approximate user counts for each bucket
    typical_n = max(1, round(users * 0.50)) if users else ""
    slow_n = max(1, round(users * 0.05)) if users else ""
    worst_n = max(1, round(users * 0.01)) if users else ""

    typical_label = f"Typical - half of {users} users were faster" if users else "Typical - median response time"
    slow_label = f"Slow - only {slow_n} of {users} users were slower" if users else "Slow - 95th percentile"
    worst_label = f"Worst Case - only {worst_n} of {users} users were this slow" if users else "Worst Case - 99th percentile"

    ax.barh([i + h for i in y], p50s, height=h, color="#0ea5e9", label=typical_label, alpha=0.85)
    ax.barh(y, p95s, height=h, color=MPL_BLUE, label=slow_label, alpha=0.85)
    ax.barh([i - h for i in y], p99s, height=h, color="#7c3aed", label=worst_label, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7, color=MPL_TEXT, fontfamily="monospace")
    ax.set_xlabel("Response Time (seconds)", fontsize=9, color=MPL_MUTED)
    ax.set_title("Response Time Breakdown by User Experience", fontsize=11, color=MPL_TEXT, fontweight="bold", pad=10)

    ax.tick_params(axis="x", colors=MPL_MUTED, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(MPL_GRID)
    ax.spines["left"].set_color(MPL_GRID)
    ax.grid(axis="x", color=MPL_GRID, linewidth=0.5, alpha=0.7)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1, fontsize=7.5,
              facecolor=MPL_BG, edgecolor=MPL_GRID, labelcolor=MPL_TEXT)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _create_status_code_chart(endpoints):
    """Horizontal stacked bar chart of success vs errors per endpoint."""
    if not endpoints:
        return None

    fig, ax = plt.subplots(figsize=(7.5, max(2.0, len(endpoints) * 0.4)))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    names = [ep["endpoint"] for ep in reversed(endpoints)]
    successes = [ep["calls"] - ep["errors"] for ep in reversed(endpoints)]
    errors = [ep["errors"] for ep in reversed(endpoints)]

    y = range(len(names))
    ax.barh(y, successes, color=MPL_GREEN, height=0.6, label="Successful", alpha=0.85)
    ax.barh(y, errors, left=successes, color=MPL_RED, height=0.6, label="Failed", alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7, color=MPL_TEXT, fontfamily="monospace")
    ax.set_xlabel("Number of Requests", fontsize=9, color=MPL_MUTED)
    ax.set_title("Successful vs Failed Requests", fontsize=11, color=MPL_TEXT, fontweight="bold", pad=10)

    ax.tick_params(axis="x", colors=MPL_MUTED, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(MPL_GRID)
    ax.spines["left"].set_color(MPL_GRID)
    ax.grid(axis="x", color=MPL_GRID, linewidth=0.5, alpha=0.7)

    ax.legend(loc="lower right", fontsize=8, facecolor=MPL_BG, edgecolor=MPL_GRID,
              labelcolor=MPL_TEXT)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ── PDF Builder ──────────────────────────────────────────────────────────

class StressTestPDF(FPDF):
    """Custom PDF for stress test reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 5, "OpenCyberRange  |  Stress Test Report", ln=True, align="R")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def _bg_rect(self, x, y, w, h, color):
        """Draw a filled rectangle."""
        self.set_fill_color(*color)
        self.rect(x, y, w, h, "F")

    def _color_dot(self, x, y, status):
        """Draw a colored status dot."""
        color_map = {"green": GREEN, "yellow": YELLOW, "red": RED}
        c = color_map.get(status, TEXT_MUTED)
        self.set_fill_color(*c)
        self.ellipse(x, y, 4, 4, "F")

    def _status_emoji(self, status):
        """Return text representation of status."""
        return {"green": "PASS", "yellow": "WARN", "red": "FAIL"}.get(status, "?")


def generate_stress_report(data: dict) -> bytes:
    """
    Generate a complete stress test PDF report.

    Args:
        data: The stress test results dict from MetricsCollector.to_dict()

    Returns:
        PDF file contents as bytes
    """
    health = _compute_health_checks(data)
    endpoints = data.get("endpoints", [])
    now = datetime.now()

    # Generate chart images
    chart_files = []

    p95_chart = _create_p95_bar_chart(endpoints)
    percentile_chart = _create_percentile_comparison(endpoints, users=data.get("users", 0))
    status_chart = _create_status_code_chart(endpoints)

    pdf = StressTestPDF()
    pdf.alias_nb_pages()

    # ── PAGE 1: Executive Summary ─────────────────────────────────────
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*TEXT_PRIMARY)
    pdf.cell(0, 12, "Stress Test Report", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, f"{now.strftime('%B %d, %Y at %H:%M CST')}", ln=True)
    pdf.ln(4)

    # Test configuration
    level = data.get("level", 1)
    users = data.get("users", 0)
    duration = data.get("duration_seconds", 0)
    total_calls = data.get("total_calls", 0)
    total_errors = data.get("total_errors", 0)
    concurrent_spawns = data.get("concurrent_spawns", 5)
    effective_users = data.get("effective_users", users)
    rps = health["rps"]

    level_names = {1: "API Only", 2: "Auth + API", 3: "Full Load (Docker)"}
    level_descriptions = {
        1: "Simulates users browsing the platform without logging in or launching labs.",
        2: "Simulates users logging in, submitting flags, requesting hints, and polling for VPN status.",
        3: "Spawns real lab containers for all users and exercises the full platform under real conditions.",
    }

    # ── Settings card ──
    card_h = 32 if level < 3 else 48
    pdf._bg_rect(10, pdf.get_y(), 190, card_h, CARD_BG)
    sy = pdf.get_y() + 3

    # Row 1: Level badge + description
    pdf.set_xy(14, sy)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*TEXT_PRIMARY)
    pdf.cell(42, 6, f"Level {level}: {level_names.get(level, '?')}")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, level_descriptions.get(level, ""))
    sy += 8

    # Row 2: Key metrics
    pdf.set_xy(14, sy)
    metrics_items = [
        ("Users", str(users)),
        ("Duration", f"{duration}s"),
        ("Total Requests", str(total_calls)),
        ("Failures", str(total_errors)),
        ("Throughput", f"{rps} req/s"),
    ]
    if level == 3:
        metrics_items.insert(1, ("Active Users", str(effective_users)))
    for label_text, value_text in metrics_items:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*TEXT_MUTED)
        lw = pdf.get_string_width(label_text + ": ")
        pdf.cell(lw + 1, 5, label_text + ": ")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT_PRIMARY)
        vw = pdf.get_string_width(value_text)
        pdf.cell(vw + 4, 5, value_text)
    sy += 7

    # Row 3: Concurrent spawns (Level 3 only)
    if level == 3:
        pdf.set_xy(14, sy)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(32, 5, "Concurrent Spawns:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.cell(8, 5, str(concurrent_spawns))
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 5, f"(max labs created in parallel during setup)")
        sy += 7

        # Row 4: Pre-spawn results
        prespawn_total = data.get("prespawn_total", 0)
        prespawn_ok = data.get("prespawn_succeeded", 0)
        prespawn_fail = data.get("prespawn_failed", 0)
        prespawn_pass = data.get("prespawn_pass", True)

        pdf.set_xy(14, sy)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(20, 5, "Lab Setup:")
        color = GREEN if prespawn_pass else RED
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*color)
        pdf.cell(10, 5, "PASS" if prespawn_pass else "FAIL")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*TEXT_PRIMARY)
        prespawn_text = f"{prespawn_ok}/{prespawn_total} labs started"
        if prespawn_fail > 0:
            prespawn_text += f" ({prespawn_fail} failed)"
        pdf.cell(0, 5, prespawn_text)
        sy += 7

    pdf.set_y(sy + 3)
    pdf.ln(2)

    # Overall health score box
    overall_color = {"green": GREEN, "yellow": YELLOW, "red": RED}[health["overall"]]
    num_checks = len(health["checks"])
    check_rows = (num_checks + 1) // 2  # 2 checks per row
    box_h = 14 + check_rows * 7 + 4     # title area + check rows + padding
    box_y = pdf.get_y()
    pdf._bg_rect(10, box_y, 190, box_h, CARD_BG)

    # Status label (left side)
    pdf.set_xy(14, box_y + 4)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*overall_color)
    pdf.cell(50, 10, health["overall_label"])

    pdf.set_xy(14, box_y + 14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(50, 6, f"{health['passed']} / {health['total']} checks passed")

    # Individual checks (right side, 2 columns with proper spacing)
    check_x = 72
    col_w = 64  # each column gets 64mm
    check_y = box_y + 4
    for i, (name, status, text) in enumerate(health["checks"]):
        row = i // 2
        col = i % 2
        cx = check_x + col * col_w
        cy = check_y + row * 7

        pdf._color_dot(cx, cy + 1.5, status)
        pdf.set_xy(cx + 5, cy)
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.set_font("Helvetica", "B", 7.5)
        nw = pdf.get_string_width(name)
        pdf.cell(nw + 2, 5, name)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(col_w - nw - 8, 5, text)

    pdf.set_y(box_y + box_h + 2)
    pdf.ln(2)

    # P95 bar chart
    if p95_chart:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(p95_chart.read())
        tmp.close()
        chart_files.append(tmp.name)

        remaining = 297 - pdf.get_y() - 15
        chart_h = min(remaining, max(50, len(endpoints) * 8 + 20))
        pdf.image(tmp.name, x=10, w=190, h=chart_h)
        pdf.ln(2)

    # ── PAGE 2: Response Time Breakdown + Success/Failure ─────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*TEXT_PRIMARY)
    pdf.cell(0, 10, "Response Time Analysis", ln=True)
    pdf.ln(2)

    if percentile_chart:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(percentile_chart.read())
        tmp.close()
        chart_files.append(tmp.name)

        chart_h = min(120, max(50, len(endpoints) * 10 + 20))
        pdf.image(tmp.name, x=10, w=190, h=chart_h)
        pdf.ln(4)

    if status_chart:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(status_chart.read())
        tmp.close()
        chart_files.append(tmp.name)

        remaining = 297 - pdf.get_y() - 15
        chart_h = min(remaining, max(40, len(endpoints) * 7 + 20))
        if chart_h > 30:
            pdf.image(tmp.name, x=10, w=190, h=chart_h)
            pdf.ln(4)

    # ── PAGE 3: Detailed Results Table ────────────────────────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*TEXT_PRIMARY)
    pdf.cell(0, 10, "Detailed Endpoint Results", ln=True)
    pdf.ln(2)

    # Table header
    col_widths = [72, 16, 20, 20, 20, 16, 16]
    headers = ["Endpoint", "Calls", "Typical", "Slow", "Worst", "Errors", "Status"]

    pdf._bg_rect(10, pdf.get_y(), 190, 7, TABLE_HEADER_BG)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*WHITE)

    x = 14
    for i, header in enumerate(headers):
        pdf.set_xy(x, pdf.get_y())
        align = "L" if i == 0 else "R"
        pdf.cell(col_widths[i], 7, header, align=align)
        x += col_widths[i]
    pdf.ln(8)

    # Table rows
    for idx, ep in enumerate(endpoints):
        is_docker = "spawn" in ep["endpoint"].lower() or "stop" in ep["endpoint"].lower()
        row_color = WHITE if idx % 2 == 0 else TABLE_ALT_ROW

        pdf._bg_rect(10, pdf.get_y(), 190, 6.5, row_color)

        x = 14
        pdf.set_font("Courier", "", 6.5)
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(col_widths[0], 6.5, ep["endpoint"][:45])
        x += col_widths[0]

        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.cell(col_widths[1], 6.5, str(ep["calls"]), align="R")
        x += col_widths[1]

        # Typical (p50)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.cell(col_widths[2], 6.5, f"{ep['p50']:.3f}s", align="R")
        x += col_widths[2]

        # Slow (p95)  - colored
        p95_color = _latency_color(ep["p95"], is_docker)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_text_color(*p95_color)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(col_widths[3], 6.5, f"{ep['p95']:.3f}s", align="R")
        x += col_widths[3]

        # Worst (p99)  - colored
        p99_color = _latency_color(ep["p99"], is_docker)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_text_color(*p99_color)
        pdf.cell(col_widths[4], 6.5, f"{ep['p99']:.3f}s", align="R")
        x += col_widths[4]

        # Errors
        pdf.set_font("Helvetica", "", 7)
        err_color = RED if ep["errors"] > 0 else TEXT_PRIMARY
        pdf.set_xy(x, pdf.get_y())
        pdf.set_text_color(*err_color)
        pdf.cell(col_widths[5], 6.5, str(ep["errors"]), align="R")
        x += col_widths[5]

        # Status
        status_color = GREEN if ep["passed"] else RED
        pdf.set_xy(x, pdf.get_y())
        pdf.set_text_color(*status_color)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(col_widths[6], 6.5, "PASS" if ep["passed"] else "FAIL", align="R")

        pdf.ln(6.5)

    # Totals row
    pdf._bg_rect(10, pdf.get_y(), 190, 7, TABLE_HEADER_BG)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*WHITE)
    x = 14
    pdf.set_xy(x, pdf.get_y())
    pdf.cell(col_widths[0], 7, "TOTAL / AVERAGE")
    x += col_widths[0]
    pdf.set_xy(x, pdf.get_y())
    pdf.cell(col_widths[1], 7, str(total_calls), align="R")
    x += col_widths[1]

    # Aggregate averages
    all_p50 = [ep["p50"] for ep in endpoints]
    all_p95 = [ep["p95"] for ep in endpoints]
    all_p99 = [ep["p99"] for ep in endpoints]
    if all_p50:
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(col_widths[2], 7, f"{sum(all_p50)/len(all_p50):.3f}s", align="R")
    x += col_widths[2]
    if all_p95:
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(col_widths[3], 7, f"{sum(all_p95)/len(all_p95):.3f}s", align="R")
    x += col_widths[3]
    if all_p99:
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(col_widths[4], 7, f"{sum(all_p99)/len(all_p99):.3f}s", align="R")
    x += col_widths[4]
    pdf.set_xy(x, pdf.get_y())
    pdf.cell(col_widths[5], 7, str(total_errors), align="R")
    pdf.ln(10)

    # Column legend with user counts
    typical_n = max(1, round(users * 0.50)) if users else "50%"
    slow_n = max(1, round(users * 0.05)) if users else "5%"
    worst_n = max(1, round(users * 0.01)) if users else "1%"
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*TEXT_MUTED)
    if users:
        legend = f"Typical = half of {users} users were faster  |  Slow = only {slow_n} of {users} were slower  |  Worst = only {worst_n} of {users} were this slow"
    else:
        legend = "Typical = median response time  |  Slow = 95th percentile  |  Worst = 99th percentile"
    pdf.cell(0, 5, legend, ln=True)
    pdf.ln(4)

    # Threshold checks
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*TEXT_PRIMARY)
    pdf.cell(0, 8, "Health Checks", ln=True)
    pdf.ln(1)

    for name, status, text in health["checks"]:
        emoji = {"green": "PASS", "yellow": "WARN", "red": "FAIL"}[status]
        color = {"green": GREEN, "yellow": YELLOW, "red": RED}[status]

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*color)
        pdf.cell(14, 6, f"[{emoji}]")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.cell(30, 6, name)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 6, text, ln=True)

    pdf.ln(4)

    # Top Errors
    top_errors = data.get("top_errors", [])
    if top_errors:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.cell(0, 8, "Top Errors", ln=True)
        pdf.ln(1)

        for i, err in enumerate(top_errors[:10]):
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*RED)
            pdf.cell(8, 5, f"{i+1}.")
            pdf.set_font("Courier", "", 6.5)
            pdf.set_text_color(*TEXT_PRIMARY)
            pdf.cell(50, 5, err.get("endpoint", ""))
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(0, 5, err.get("error", "")[:100], ln=True)

        pdf.ln(2)

    # Recommendations
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*TEXT_PRIMARY)
    pdf.cell(0, 8, "Recommendations", ln=True)
    pdf.ln(1)

    recommendations = []
    for ep in endpoints:
        is_docker = "spawn" in ep["endpoint"].lower() or "stop" in ep["endpoint"].lower()
        label = _latency_label(ep["p95"], is_docker)
        if label == "red":
            recommendations.append(f"CRITICAL: {ep['endpoint']} is too slow ({ep['p95']:.3f}s)  - investigate database performance or server capacity")
        elif label == "yellow":
            recommendations.append(f"WARNING: {ep['endpoint']} is approaching the slowness threshold ({ep['p95']:.3f}s)  - consider optimization")

    if data.get("error_rate", 0) > 1:
        recommendations.append(f"Error rate is {data['error_rate']}%  - check server logs for the cause of failures")

    if rps < 50:
        recommendations.append(f"Throughput is {rps} requests/sec  - consider adding server capacity or optimizing slow endpoints")

    if not recommendations:
        recommendations.append("All metrics are within healthy ranges. The system is performing well under the tested load.")

    for rec in recommendations:
        pdf.set_font("Helvetica", "", 8)
        if "CRITICAL" in rec:
            pdf.set_text_color(*RED)
            pdf.cell(4, 5, "")
        elif "WARNING" in rec:
            pdf.set_text_color(*YELLOW)
            pdf.cell(4, 5, "")
        else:
            pdf.set_text_color(*GREEN)
            pdf.cell(4, 5, "")
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.multi_cell(0, 5, rec)
        pdf.ln(1)

    # Generate output
    output = pdf.output()

    # Cleanup temp files
    for f in chart_files:
        try:
            os.unlink(f)
        except Exception:
            pass

    return bytes(output)
