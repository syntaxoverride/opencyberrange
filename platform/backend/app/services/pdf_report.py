"""
PDF grade report generation for courses.
Uses fpdf2 to generate downloadable PDF reports.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fpdf import FPDF
from typing import List

LOCAL_TZ = ZoneInfo("America/Chicago")


def _sanitize_for_pdf(text: str) -> str:
    """Replace Unicode characters that Helvetica can't render (latin-1 only)."""
    text = (
        text
        .replace("\u2192", "->")   # →
        .replace("\u2014", "--")   # —
        .replace("\u2013", "-")    # –
        .replace("\u2018", "'")    # '
        .replace("\u2019", "'")    # '
        .replace("\u201c", '"')    # "
        .replace("\u201d", '"')    # "
        .replace("\u2026", "...")  # …
        .replace("\u2022", "*")    # •
        .replace("\u00b7", ".")    # ·
    )
    return text.encode("latin-1", errors="replace").decode("latin-1")


class GradeReportPDF(FPDF):
    """Custom PDF class with header/footer for grade reports."""

    def __init__(self, course_name: str, course_code: str):
        super().__init__()
        self.course_name = course_name
        self.course_code = course_code

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"OpenCyberRange - {self.course_code}", ln=True, align="R")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_student_report(
    student: dict,
    course: dict,
    lab_scores: List[dict],
    achievements: List[dict],
) -> bytes:
    """Generate a PDF grade report for a single student.

    Args:
        student: {username, student_id, email}
        course: {name, code, semester, instructor_name, start_date, end_date}
        lab_scores: [{lab_name, score, max_score, attempts, hints_used,
                      time_minutes, completed_at}]
        achievements: [{type, label, lab_name}]

    Returns:
        PDF file bytes.
    """
    pdf = GradeReportPDF(
        _sanitize_for_pdf(str(course["name"])),
        _sanitize_for_pdf(str(course["code"])),
    )
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    _add_student_page(pdf, student, course, lab_scores, achievements)
    return pdf.output()


def generate_class_report(
    course: dict,
    students_data: List[dict],
) -> bytes:
    """Generate a PDF with one page per student.

    Args:
        course: {name, code, semester, instructor_name, start_date, end_date}
        students_data: [{student, lab_scores, achievements}]

    Returns:
        PDF file bytes.
    """
    pdf = GradeReportPDF(
        _sanitize_for_pdf(str(course["name"])),
        _sanitize_for_pdf(str(course["code"])),
    )
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    for entry in students_data:
        _add_student_page(
            pdf,
            entry["student"],
            course,
            entry["lab_scores"],
            entry["achievements"],
        )

    return pdf.output()


def _add_student_page(
    pdf: FPDF,
    student: dict,
    course: dict,
    lab_scores: List[dict],
    achievements: List[dict],
):
    """Add a single student report page to the PDF."""
    pdf.add_page()

    # Sanitise all dynamic text up-front
    c_name = _sanitize_for_pdf(str(course["name"]))
    c_code = _sanitize_for_pdf(str(course["code"]))
    c_semester = _sanitize_for_pdf(str(course["semester"]))
    c_instructor = _sanitize_for_pdf(str(course["instructor_name"]))
    s_username = _sanitize_for_pdf(str(student["username"]))
    s_email = _sanitize_for_pdf(str(student["email"]))

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, "Grade Report", ln=True, align="C")
    pdf.ln(6)

    # Course info box
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(10, pdf.get_y(), 190, 28, style="DF")
    y_start = pdf.get_y() + 3
    pdf.set_xy(14, y_start)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(90, 6, c_name, ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Code: {c_code}", ln=True, align="R")
    pdf.set_x(14)
    pdf.cell(90, 5, f"Semester: {c_semester}", ln=False)
    pdf.cell(0, 5, f"Instructor: {c_instructor}", ln=True, align="R")
    pdf.set_x(14)
    start = course["start_date"]
    end = course["end_date"]
    if isinstance(start, datetime):
        start = start.strftime("%Y-%m-%d")
    if isinstance(end, datetime):
        end = end.strftime("%Y-%m-%d")
    pdf.cell(0, 5, f"Period: {start} to {end}", ln=True)
    pdf.ln(10)

    # Student info
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Student Information", ln=True)
    pdf.set_draw_color(59, 130, 246)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(60, 6, f"Name: {s_username}", ln=False)
    pdf.cell(0, 6, f"Email: {s_email}", ln=True)
    pdf.ln(6)

    # Score summary
    total_score = sum(s.get("score", 0) for s in lab_scores)
    total_max = sum(s.get("max_score", 250) for s in lab_scores)
    labs_completed = sum(1 for s in lab_scores if s.get("completed_at"))
    total_labs = len(lab_scores)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Performance Summary", ln=True)
    pdf.set_draw_color(59, 130, 246)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 65, 85)
    pct = round(total_score / total_max * 100) if total_max > 0 else 0
    pdf.cell(0, 7, f"Total Score: {total_score} / {total_max} ({pct}%)", ln=True)
    pdf.cell(0, 7, f"Labs Completed: {labs_completed} / {total_labs}", ln=True)
    pdf.ln(4)

    # Lab results table
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Lab Results", ln=True)
    pdf.set_draw_color(59, 130, 246)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # Table header
    col_widths = [62, 20, 22, 20, 22, 44]
    headers = ["Lab", "Score", "Attempts", "Hints", "Time", "Completed (CT)"]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(59, 130, 246)
    pdf.set_text_color(255, 255, 255)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, header, border=0, fill=True, align="C")
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 9)
    for idx, lab_score in enumerate(lab_scores):
        if idx % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(51, 65, 85)

        name = _sanitize_for_pdf(str(lab_score["lab_name"]))
        if len(name) > 32:
            name = name[:30] + ".."
        pdf.cell(col_widths[0], 6, name, border=0, fill=True)
        pdf.cell(col_widths[1], 6, str(lab_score.get("score", "-")), border=0, fill=True, align="C")
        pdf.cell(col_widths[2], 6, str(lab_score.get("attempts", 0)), border=0, fill=True, align="C")
        pdf.cell(col_widths[3], 6, str(lab_score.get("hints_used", 0)), border=0, fill=True, align="C")

        time_val = lab_score.get("time_minutes")
        time_str = f"{time_val}m" if time_val else "-"
        pdf.cell(col_widths[4], 6, time_str, border=0, fill=True, align="C")

        completed = lab_score.get("completed_at")
        if completed:
            if isinstance(completed, datetime):
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=timezone.utc)
                completed = completed.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
            pdf.cell(col_widths[5], 6, str(completed), border=0, fill=True, align="C")
        else:
            pdf.set_text_color(180, 180, 180)
            pdf.cell(col_widths[5], 6, "Incomplete", border=0, fill=True, align="C")
            pdf.set_text_color(51, 65, 85)
        pdf.ln()

    pdf.ln(6)

    # Achievements
    if achievements:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, "Achievements", ln=True)
        pdf.set_draw_color(59, 130, 246)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        for ach in achievements:
            ach_lab = f" ({_sanitize_for_pdf(str(ach['lab_name']))})" if ach.get("lab_name") else ""
            ach_label = _sanitize_for_pdf(str(ach["label"]))
            pdf.cell(0, 6, f"  - {ach_label}{ach_lab}", ln=True)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "No achievements earned yet.", ln=True)

    # Generation timestamp
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0, 6,
        f"Generated: {datetime.now(timezone.utc).astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M %Z')} | OpenCyberRange",
        ln=True, align="C"
    )


# ==================== Dashboard Report ====================

class DashboardReportPDF(FPDF):
    """Custom PDF class for Ops Center dashboard reports."""

    def __init__(self, title: str):
        super().__init__()
        self.title_text = title

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"OpenCyberRange - {self.title_text}", ln=True, align="R")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_dashboard_report(
    filters: dict,
    student: dict,
    students: List[dict],
    pulse: List[dict],
    pulse_granularity: str,
    events: List[dict],
) -> bytes:
    """Generate a PDF report for a filtered dashboard view.

    Args:
        filters: {range_label, start, end, course_code, course_name, scope_label}
        student: Optional single-student detail dict {username, email, role,
                 flags_correct, flags_wrong, labs_completed, sessions_started}.
                 None when the report is a window-wide summary.
        students: List of per-student summary rows (used when `student` is None).
                  Each row: {username, flags_correct, flags_wrong, labs_completed,
                  sessions_started}.
        pulse: Pulse buckets [{hour, concurrent_labs, flags_submitted}, ...]
        pulse_granularity: 'hour' or 'day'
        events: Activity events (already scoped/filtered), newest first.
    """
    title = _sanitize_for_pdf(filters.get("range_label", "Dashboard Report"))
    pdf = DashboardReportPDF(title)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, "Ops Center Report", ln=True, align="C")
    pdf.ln(2)

    # Filter summary box
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    box_y = pdf.get_y()
    box_h = 22
    pdf.rect(10, box_y, 190, box_h, style="DF")
    pdf.set_xy(14, box_y + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, _sanitize_for_pdf(filters.get("scope_label", "All activity")), ln=True)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 5, f"Range: {_sanitize_for_pdf(filters.get('range_label', ''))}", ln=True)
    pdf.set_x(14)
    start_lbl = filters.get("start_local", "")
    end_lbl = filters.get("end_local", "")
    pdf.cell(0, 5, f"Window: {start_lbl} to {end_lbl} (CT)", ln=True)
    pdf.set_y(box_y + box_h + 6)

    # Student details section
    if student:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, "Student Details", ln=True)
        pdf.set_draw_color(59, 130, 246)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(60, 6, f"Username: {_sanitize_for_pdf(str(student.get('username', '')))}", ln=False)
        pdf.cell(0, 6, f"Email: {_sanitize_for_pdf(str(student.get('email', '') or '-'))}", ln=True)
        pdf.cell(60, 6, f"Role: {_sanitize_for_pdf(str(student.get('role', 'student')))}", ln=False)
        pdf.cell(0, 6, f"Flags Solved: {student.get('flags_correct', 0)}", ln=True)
        pdf.cell(60, 6, f"Wrong Flags: {student.get('flags_wrong', 0)}", ln=False)
        pdf.cell(0, 6, f"Labs Completed: {student.get('labs_completed', 0)}", ln=True)
        pdf.cell(0, 6, f"Sessions Started: {student.get('sessions_started', 0)}", ln=True)
        pdf.ln(4)

    # Activity graphic (bar chart from pulse data)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Activity", ln=True)
    pdf.set_draw_color(59, 130, 246)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    _draw_pulse_chart(pdf, pulse, pulse_granularity)
    pdf.ln(4)

    # Per-student summary (when not single-student)
    if not student and students:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, f"Students in Window ({len(students)})", ln=True)
        pdf.set_draw_color(59, 130, 246)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        col_widths = [70, 30, 30, 30, 30]
        headers = ["Student", "Solved", "Wrong", "Completed", "Sessions"]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(59, 130, 246)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 7, h, border=0, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for idx, s in enumerate(students):
            if idx % 2 == 0:
                pdf.set_fill_color(248, 250, 252)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(51, 65, 85)
            uname = _sanitize_for_pdf(str(s.get("username", "-")))
            if len(uname) > 38:
                uname = uname[:36] + ".."
            pdf.cell(col_widths[0], 6, uname, border=0, fill=True)
            pdf.cell(col_widths[1], 6, str(s.get("flags_correct", 0)), border=0, fill=True, align="C")
            pdf.cell(col_widths[2], 6, str(s.get("flags_wrong", 0)), border=0, fill=True, align="C")
            pdf.cell(col_widths[3], 6, str(s.get("labs_completed", 0)), border=0, fill=True, align="C")
            pdf.cell(col_widths[4], 6, str(s.get("sessions_started", 0)), border=0, fill=True, align="C")
            pdf.ln()
        pdf.ln(4)

    # Logs
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, f"Activity Log ({len(events)})", ln=True)
    pdf.set_draw_color(59, 130, 246)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    col_widths = [36, 38, 36, 80]
    headers = ["Time (CT)", "User", "Event", "Target"]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(59, 130, 246)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=0, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for idx, ev in enumerate(events):
        if idx % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(51, 65, 85)

        ts = ev.get("created_at")
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_str = ts.astimezone(LOCAL_TZ).strftime("%m-%d %H:%M:%S")
        else:
            ts_str = str(ts or "-")[:19].replace("T", " ")

        user = _sanitize_for_pdf(str(ev.get("actor_username") or "System"))
        if len(user) > 20:
            user = user[:18] + ".."
        label = _sanitize_for_pdf(str(ev.get("event_label") or ev.get("event_type") or "-"))
        if len(label) > 20:
            label = label[:18] + ".."
        target = _sanitize_for_pdf(str(ev.get("target_label") or "-"))
        if len(target) > 48:
            target = target[:46] + ".."

        pdf.cell(col_widths[0], 5, ts_str, border=0, fill=True)
        pdf.cell(col_widths[1], 5, user, border=0, fill=True)
        pdf.cell(col_widths[2], 5, label, border=0, fill=True)
        pdf.cell(col_widths[3], 5, target, border=0, fill=True)
        pdf.ln()

    # Footer timestamp
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0, 6,
        f"Generated: {datetime.now(timezone.utc).astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M %Z')} | OpenCyberRange",
        ln=True, align="C"
    )

    return pdf.output()


def _draw_pulse_chart(pdf: FPDF, pulse: List[dict], granularity: str):
    """Render pulse buckets as a grouped bar chart with X/Y axes."""
    # Outer block
    outer_x = 12
    outer_y = pdf.get_y()
    outer_w = 186
    outer_h = 58  # extra room for two-line X-axis labels

    # Axis gutter sizes (inside the outer block)
    y_axis_w = 12   # space for Y-axis labels on the left
    x_axis_h = 12   # room for two-line X-axis labels (time + date)
    top_pad = 2

    plot_x = outer_x + y_axis_w
    plot_y = outer_y + top_pad
    plot_w = outer_w - y_axis_w - 2
    plot_h = outer_h - top_pad - x_axis_h

    # Plot background
    pdf.set_draw_color(203, 213, 225)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(plot_x, plot_y, plot_w, plot_h, style="DF")

    if not pulse:
        pdf.set_xy(plot_x, plot_y + plot_h / 2 - 3)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(plot_w, 6, "No activity in this window", align="C")
        pdf.set_y(outer_y + outer_h)
        return

    raw_max = max(
        max(p.get("concurrent_labs", 0), p.get("flags_submitted", 0))
        for p in pulse
    )
    raw_max = max(raw_max, 1)

    # Round Y max to a "nice" number so ticks are readable
    def _nice_ceiling(v: int) -> int:
        if v <= 5:
            return 5
        if v <= 10:
            return 10
        # Round up to nearest power-of-10 / 2
        import math
        exp = 10 ** int(math.floor(math.log10(v)))
        for mult in (1, 2, 2.5, 5, 10):
            cand = mult * exp
            if cand >= v:
                return int(cand)
        return int(10 * exp)

    y_max = _nice_ceiling(raw_max)

    # ── Y-axis gridlines + labels (0, mid, max) ─────────────
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.set_draw_color(226, 232, 240)
    y_ticks = [0, y_max // 2, y_max] if y_max >= 2 else [0, y_max]
    for tick in y_ticks:
        frac = tick / y_max if y_max else 0
        ty = plot_y + plot_h - frac * plot_h
        # Gridline
        if tick != 0:
            pdf.line(plot_x, ty, plot_x + plot_w, ty)
        # Label
        pdf.set_xy(outer_x, ty - 1.8)
        pdf.cell(y_axis_w - 1, 3.5, str(tick), align="R")

    # ── Bars ────────────────────────────────────────────────
    n = len(pulse)
    slot_w = plot_w / n
    bar_w = max(0.6, min(slot_w / 2 - 0.4, 3.5))

    for i, p in enumerate(pulse):
        slot_x = plot_x + i * slot_w
        sessions = p.get("concurrent_labs", 0)
        flags = p.get("flags_submitted", 0)

        if sessions > 0:
            h = (sessions / y_max) * plot_h
            pdf.set_fill_color(59, 130, 246)
            pdf.rect(slot_x + slot_w / 2 - bar_w - 0.2, plot_y + plot_h - h, bar_w, h, style="F")

        if flags > 0:
            h = (flags / y_max) * plot_h
            pdf.set_fill_color(34, 197, 94)
            pdf.rect(slot_x + slot_w / 2 + 0.2, plot_y + plot_h - h, bar_w, h, style="F")

    # ── X-axis labels (first, ~25%, ~50%, ~75%, last) ───────
    def _parse_bucket(bucket_key: str):
        try:
            d = datetime.fromisoformat(bucket_key.replace("Z", "+00:00"))
            return d.astimezone(LOCAL_TZ)
        except Exception:
            return None

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    # Target ~5 tick labels, clamped to n
    num_labels = min(5, n)
    if num_labels == 1:
        label_idxs = [0]
    else:
        step = (n - 1) / (num_labels - 1)
        label_idxs = sorted({int(round(i * step)) for i in range(num_labels)})

    axis_y = plot_y + plot_h
    pdf.set_draw_color(150, 160, 175)
    pdf.line(plot_x, axis_y, plot_x + plot_w, axis_y)
    for idx in label_idxs:
        lx = plot_x + idx * slot_w + slot_w / 2
        pdf.line(lx, axis_y, lx, axis_y + 1.2)
        d_local = _parse_bucket(pulse[idx].get("hour", ""))
        tw = 20
        if d_local is None:
            line1 = pulse[idx].get("hour", "")[:10]
            line2 = ""
        elif granularity == "day":
            # Day granularity: single-line date, already unambiguous
            line1 = d_local.strftime("%a")
            line2 = d_local.strftime("%m-%d")
        else:
            # Hourly: always show date under the time so spikes are datable
            line1 = d_local.strftime("%H:%M")
            line2 = d_local.strftime("%a %m-%d")
        pdf.set_xy(lx - tw / 2, axis_y + 1.3)
        pdf.cell(tw, 3.2, line1, align="C")
        if line2:
            pdf.set_xy(lx - tw / 2, axis_y + 4.5)
            pdf.cell(tw, 3.2, line2, align="C")

    # ── Axis titles ─────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 130, 145)
    # Y-axis title (just above the plot, inside the gutter)
    pdf.set_xy(outer_x, outer_y - 3)
    pdf.cell(30, 3, "Count", ln=False)
    # X-axis title under the labels
    time_label = "Date (CT)" if granularity == "day" else "Time / Date (CT)"
    pdf.set_xy(plot_x, outer_y + outer_h - 3.2)
    pdf.cell(plot_w, 3, time_label, align="C")

    pdf.set_y(outer_y + outer_h + 1)

    # ── Legend ──────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 8)
    pdf.set_fill_color(59, 130, 246)
    pdf.rect(outer_x, pdf.get_y() + 1, 3, 3, style="F")
    pdf.set_text_color(100, 116, 139)
    pdf.set_xy(outer_x + 4, pdf.get_y())
    pdf.cell(40, 5, "Exercise Sessions", ln=False)
    pdf.set_fill_color(34, 197, 94)
    pdf.rect(outer_x + 44, pdf.get_y() + 1, 3, 3, style="F")
    pdf.set_xy(outer_x + 48, pdf.get_y())
    pdf.cell(40, 5, "Flags Submitted", ln=False)
    pdf.set_xy(outer_x + 90, pdf.get_y())
    pdf.cell(0, 5, f"Peak: {raw_max}  ({granularity}ly buckets, {len(pulse)} points)", ln=True)
