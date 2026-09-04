#!/usr/bin/env python3
"""
Demo Class Seed Script  [DEVELOPMENT ONLY — do not run in production]
Creates a demo instructor, 6 demo students with varied statistics,
a demo course, and enrolls everyone — showcasing all platform features.
Uses hardcoded credentials for demo purposes only.

Run inside Docker:
  docker compose exec backend python /app/app/scripts/seed_demo_class.py
"""

import os
import sys
import json
import secrets
from datetime import datetime, timedelta, timezone

_missing = []
for _mod in ['sqlalchemy', 'passlib']:
    try:
        __import__(_mod)
    except ImportError:
        _missing.append(_mod)

if _missing:
    print("Error: Missing required Python modules: " + ", ".join(_missing))
    print("This script runs inside the Docker container:")
    print("  docker compose exec backend python /app/app/scripts/seed_demo_class.py")
    sys.exit(1)

sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://labuser:labpass@db:5432/labdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

NOW = datetime.now(timezone.utc)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO ACCOUNTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTRUCTOR = {
    "username": "dr_martinez",
    "email": "martinez@university.edu",
    "password": "Instructor2026!",
    "role": "instructor",
}

STUDENTS = [
    {
        "username": "alex_chen",
        "email": "achen@university.edu",
        "student_id": "STU2026001",
        # Top performer — fast, few hints, high completion
        "personality": "star",
    },
    {
        "username": "jordan_patel",
        "email": "jpatel@university.edu",
        "student_id": "STU2026002",
        # Solid performer — steady progress, occasionally uses hints
        "personality": "steady",
    },
    {
        "username": "sam_okafor",
        "email": "sokafor@university.edu",
        "student_id": "STU2026003",
        # Struggles early, improves over time
        "personality": "improver",
    },
    {
        "username": "taylor_nguyen",
        "email": "tnguyen@university.edu",
        "student_id": "STU2026004",
        # Uses lots of hints, takes time, but gets there
        "personality": "methodical",
    },
    {
        "username": "riley_jackson",
        "email": "rjackson@university.edu",
        "student_id": "STU2026005",
        # Behind — only completed some labs, still in progress
        "personality": "behind",
    },
    {
        "username": "morgan_brooks",
        "email": "mbrooks@university.edu",
        "student_id": "STU2026006",
        # Inactive — enrolled but barely started
        "personality": "inactive",
    },
]

PASSWORD = "Student2026!"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STUDENT PROFILES — defines how each personality completes labs
# Returns (attempts, hints_used, time_ratio) per lab index
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_profile(personality, lab_index, total_labs):
    """Return (attempts, hints_used, time_ratio, completed) for a student personality."""

    if personality == "star":
        # Crushes every lab — fast, no hints, first attempt
        profiles = [
            (1, 0, 0.20),  # blazing fast
            (1, 0, 0.25),
            (1, 0, 0.30),
            (1, 0, 0.22),
            (1, 1, 0.35),  # used one hint once
            (1, 0, 0.28),
            (1, 0, 0.18),  # fastest yet
            (1, 0, 0.32),
        ]
        p = profiles[lab_index % len(profiles)]
        return (*p, True)

    elif personality == "steady":
        # Consistent B+ student
        profiles = [
            (2, 0, 0.55),
            (1, 0, 0.60),
            (1, 1, 0.65),
            (1, 0, 0.50),
            (2, 1, 0.70),
            (1, 0, 0.45),
            (1, 0, 0.55),
            (2, 0, 0.60),
        ]
        p = profiles[lab_index % len(profiles)]
        return (*p, True)

    elif personality == "improver":
        # Rough start, gets better over time
        profiles = [
            (5, 2, 1.30),  # really struggled
            (4, 2, 1.10),
            (3, 1, 0.90),
            (2, 1, 0.75),
            (2, 0, 0.65),  # getting better
            (1, 0, 0.55),
            (1, 0, 0.50),  # confident now
            (1, 0, 0.45),
        ]
        p = profiles[lab_index % len(profiles)]
        return (*p, True)

    elif personality == "methodical":
        # Slow and careful, uses hints but always finishes
        profiles = [
            (2, 2, 0.90),
            (3, 2, 0.95),
            (2, 1, 0.85),
            (1, 2, 1.00),
            (2, 2, 0.80),
            (1, 1, 0.75),
            (2, 1, 0.85),
            (1, 2, 0.90),
        ]
        p = profiles[lab_index % len(profiles)]
        return (*p, True)

    elif personality == "behind":
        # Only completed first 4 labs
        if lab_index >= 4:
            return (0, 0, 0, False)
        profiles = [
            (3, 1, 0.80),
            (2, 1, 0.70),
            (4, 2, 1.00),
            (2, 0, 0.65),
        ]
        p = profiles[lab_index]
        return (*p, True)

    elif personality == "inactive":
        # Only completed first lab, started second
        if lab_index == 0:
            return (3, 2, 1.20, True)
        else:
            return (0, 0, 0, False)

    return (1, 0, 0.50, True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def upsert_user(db, username, email, password, role, student_id=None, days_ago=30):
    """Create or update user. Returns user_id."""
    row = db.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
    hashed = pwd_context.hash(password)
    created = (NOW - timedelta(days=days_ago)).isoformat()

    if row:
        user_id = row[0]
        db.execute(text("""
            UPDATE users SET email=:e, hashed_password=:hp, role=:r, student_id=:sid,
                is_active=true, is_approved=true, is_locked=false, failed_attempts=0,
                vpn_registered=true, must_change_password=false
            WHERE id = :id
        """), {"e": email, "hp": hashed, "r": role, "sid": student_id, "id": user_id})
    else:
        db.execute(text("""
            INSERT INTO users (username, email, hashed_password, role, student_id,
                is_active, is_approved, vpn_registered, must_change_password, created_at)
            VALUES (:u, :e, :hp, :r, :sid, true, true, true, false, :ca)
        """), {"u": username, "e": email, "hp": hashed, "r": role, "sid": student_id, "ca": created})
        db.commit()
        user_id = db.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()[0]

    db.commit()
    return user_id


def log_event(db, event_type, actor_id, target_type, target_id, target_label, created_at=None):
    ts = (created_at or NOW).isoformat()
    db.execute(text("""
        INSERT INTO activity_events (event_type, actor_id, target_type, target_id, target_label, created_at)
        VALUES (:et, :ai, :tt, :ti, :tl, :ca)
    """), {"et": event_type, "ai": actor_id, "tt": target_type, "ti": target_id, "tl": target_label, "ca": ts})


def award_achievement(db, user_id, course_id, lab_id, achievement_type, awarded_at=None):
    if lab_id:
        existing = db.execute(text(
            "SELECT id FROM achievements WHERE user_id=:u AND course_id=:c AND lab_id=:l AND achievement_type=:t"
        ), {"u": user_id, "c": course_id, "l": lab_id, "t": achievement_type}).fetchone()
    else:
        existing = db.execute(text(
            "SELECT id FROM achievements WHERE user_id=:u AND course_id=:c AND lab_id IS NULL AND achievement_type=:t"
        ), {"u": user_id, "c": course_id, "t": achievement_type}).fetchone()

    if existing:
        return

    ts = (awarded_at or NOW).isoformat()
    db.execute(text("""
        INSERT INTO achievements (user_id, course_id, lab_id, achievement_type, awarded_at)
        VALUES (:u, :c, :l, :t, :at)
    """), {"u": user_id, "c": course_id, "l": lab_id, "t": achievement_type, "at": ts})

    log_event(db, "achievement_awarded", user_id, "achievement", lab_id, achievement_type, created_at=datetime.fromisoformat(ts))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN SEED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def seed_demo_class():
    db = SessionLocal()
    try:
        _run(db)
    except Exception as e:
        db.rollback()
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def _run(db):
    print("=" * 60)
    print("  OpenCyberRange Demo Class Seeder")
    print("=" * 60)

    # ── 1. Create Instructor ─────────────────────────────────
    print("\n[1/6] Creating demo instructor...")
    instructor_id = upsert_user(
        db, INSTRUCTOR["username"], INSTRUCTOR["email"],
        INSTRUCTOR["password"], INSTRUCTOR["role"], days_ago=60
    )
    print(f"  Instructor: {INSTRUCTOR['username']} (id={instructor_id})")

    # ── 2. Create Demo Course ────────────────────────────────
    print("\n[2/6] Creating demo course...")
    course_row = db.execute(text(
        "SELECT id FROM courses WHERE code = :c AND instructor_id = :i"
    ), {"c": "CYB-3350", "i": instructor_id}).fetchone()

    invite_code = secrets.token_urlsafe(6)[:8]
    course_start = NOW - timedelta(days=28)
    course_end = NOW + timedelta(days=60)

    if course_row:
        course_id = course_row[0]
        db.execute(text("""
            UPDATE courses SET name=:n, semester=:s, description=:d,
                start_date=:sd, end_date=:ed, is_active=true, is_archived=false
            WHERE id = :id
        """), {
            "n": "Cyber Security Fundamentals",
            "s": "Spring 2026",
            "d": "Introduction to penetration testing and vulnerability assessment. "
                 "Students progress through Linux, Web, and Windows attack scenarios.",
            "sd": course_start.isoformat(),
            "ed": course_end.isoformat(),
            "id": course_id,
        })
        print(f"  Updated existing course (id={course_id})")
    else:
        db.execute(text("""
            INSERT INTO courses (name, code, semester, description, invite_code,
                instructor_id, start_date, end_date, is_active)
            VALUES (:n, :c, :s, :d, :inv, :i, :sd, :ed, true)
        """), {
            "n": "Cyber Security Fundamentals",
            "c": "CYB-3350",
            "s": "Spring 2026",
            "d": "Introduction to penetration testing and vulnerability assessment. "
                 "Students progress through Linux, Web, and Windows attack scenarios.",
            "inv": invite_code,
            "i": instructor_id,
            "sd": course_start.isoformat(),
            "ed": course_end.isoformat(),
        })
        db.commit()
        course_id = db.execute(text(
            "SELECT id FROM courses WHERE code = :c AND instructor_id = :i"
        ), {"c": "CYB-3350", "i": instructor_id}).fetchone()[0]
        print(f"  Created course 'Cyber Security Fundamentals' (id={course_id})")

    db.commit()

    # ── 3. Assign Labs to Course ─────────────────────────────
    print("\n[3/6] Assigning labs to course...")

    # Pick 8 labs across Linux, Web, and Windows tracks for variety
    lab_rows = db.execute(text("""
        SELECT l.id, l.name, l.slug, l.duration_minutes, l.flag_hash, l.hints,
               t.name as track_name
        FROM labs l
        JOIN levels lv ON l.level_id = lv.id
        JOIN tracks t ON lv.track_id = t.id
        WHERE l.is_active = true AND l.flag_hash IS NOT NULL
        ORDER BY t.sort_order, lv.level_number, l.sort_order, l.id
        LIMIT 8
    """)).fetchall()

    labs = []
    for i, row in enumerate(lab_rows):
        labs.append({
            "id": row[0], "name": row[1], "slug": row[2],
            "duration": row[3] or 60, "flag_hash": row[4],
            "hint_count": len(json.loads(row[5])) if row[5] else 0,
            "track": row[6],
        })

        # Assign to course if not already
        exists = db.execute(text(
            "SELECT id FROM course_lab_assignments WHERE course_id=:c AND lab_id=:l"
        ), {"c": course_id, "l": row[0]}).fetchone()
        if not exists:
            db.execute(text("""
                INSERT INTO course_lab_assignments (course_id, lab_id, sort_order)
                VALUES (:c, :l, :s)
            """), {"c": course_id, "l": row[0], "s": i})

    db.commit()

    for lab in labs:
        print(f"  [{lab['track'][:12]:>12}] {lab['name']}")
    print(f"  Total: {len(labs)} labs assigned")

    # ── 4. Create Students ───────────────────────────────────
    print("\n[4/6] Creating demo students...")
    student_ids = {}
    for s in STUDENTS:
        sid = upsert_user(db, s["username"], s["email"], PASSWORD, "student",
                          student_id=s.get("student_id"), days_ago=25)
        student_ids[s["username"]] = {"id": sid, "personality": s["personality"]}
        print(f"  {s['username']:20s} ({s['personality']:10s}) id={sid}")

    # ── 5. Enroll Students ───────────────────────────────────
    print("\n[5/6] Enrolling students...")
    for i, s in enumerate(STUDENTS):
        user_id = student_ids[s["username"]]["id"]
        enrolled = db.execute(text(
            "SELECT id FROM course_enrollments WHERE course_id=:c AND user_id=:u"
        ), {"c": course_id, "u": user_id}).fetchone()

        enroll_time = course_start + timedelta(hours=i * 4 + 2)  # stagger enrollments
        if not enrolled:
            db.execute(text("""
                INSERT INTO course_enrollments (course_id, user_id, enrolled_at)
                VALUES (:c, :u, :ea)
            """), {"c": course_id, "u": user_id, "ea": enroll_time.isoformat()})
            log_event(db, "course_enrolled", user_id, "course", course_id,
                      "Enrolled in course", created_at=enroll_time)

    db.commit()
    print(f"  {len(STUDENTS)} students enrolled")

    # ── 6. Seed Lab Data Per Student ─────────────────────────
    print("\n[6/6] Seeding lab completions, attempts, and achievements...")

    # Track who got first_blood on each lab (first to complete)
    first_blood_tracker = {}  # lab_id -> (user_id, completed_at)

    # Collect all student completion data first to determine first_blood
    all_completions = []

    for s in STUDENTS:
        user_id = student_ids[s["username"]]["id"]
        personality = s["personality"]
        enroll_offset = STUDENTS.index(s)
        enroll_time = course_start + timedelta(hours=enroll_offset * 4 + 2)

        # Clear old demo data for this user
        db.execute(text("DELETE FROM flag_attempts WHERE user_id = :u"), {"u": user_id})
        db.execute(text("DELETE FROM lab_completions WHERE user_id = :u"), {"u": user_id})
        db.execute(text("DELETE FROM achievements WHERE user_id = :u AND course_id = :c"),
                   {"u": user_id, "c": course_id})
        db.execute(text("""
            DELETE FROM activity_events WHERE actor_id = :u AND event_type IN
            ('lab_started','lab_stopped','lab_completed','flag_correct',
             'flag_incorrect','hint_used','achievement_awarded','vpn_downloaded')
        """), {"u": user_id})
        db.execute(text("DELETE FROM lab_sessions WHERE user_id = :u"), {"u": user_id})
        db.commit()

        # Registration and VPN events
        log_event(db, "user_registered", user_id, "user", user_id, s["username"],
                  created_at=NOW - timedelta(days=25))
        log_event(db, "vpn_downloaded", user_id, "user", user_id, s["username"],
                  created_at=enroll_time + timedelta(hours=1))

        print(f"\n  {s['username']} ({personality}):")

        for lab_idx, lab in enumerate(labs):
            attempts, hints_used, time_ratio, completed = get_profile(personality, lab_idx, len(labs))

            if not completed:
                # Student hasn't done this lab yet — maybe started it
                if personality == "behind" and lab_idx == 4:
                    # Started but didn't finish
                    start_time = enroll_time + timedelta(days=lab_idx * 2 + 1, hours=3)
                    db.execute(text("""
                        INSERT INTO lab_sessions (user_id, lab_id, status, started_at, expires_at)
                        VALUES (:u, :l, 'stopped', :sa, :ea)
                    """), {
                        "u": user_id, "l": lab["id"],
                        "sa": start_time.isoformat(),
                        "ea": (start_time + timedelta(hours=2)).isoformat(),
                    })
                    log_event(db, "lab_started", user_id, "lab", lab["id"],
                              lab["name"], created_at=start_time)
                    print(f"    [{lab_idx+1}] {lab['name'][:40]:40s} - started only")
                elif personality == "inactive" and lab_idx == 1:
                    # Started second lab but gave up
                    start_time = enroll_time + timedelta(days=3, hours=5)
                    db.execute(text("""
                        INSERT INTO lab_sessions (user_id, lab_id, status, started_at, expires_at)
                        VALUES (:u, :l, 'expired', :sa, :ea)
                    """), {
                        "u": user_id, "l": lab["id"],
                        "sa": start_time.isoformat(),
                        "ea": (start_time + timedelta(hours=2)).isoformat(),
                    })
                    log_event(db, "lab_started", user_id, "lab", lab["id"],
                              lab["name"], created_at=start_time)
                    log_event(db, "session_expired", user_id, "lab", lab["id"],
                              lab["name"], created_at=start_time + timedelta(hours=2))
                    print(f"    [{lab_idx+1}] {lab['name'][:40]:40s} - expired")
                continue

            duration = lab["duration"]
            time_spent = max(5, int(duration * time_ratio))

            # Spread completions over realistic timeframe
            # Star student completes fastest (every 1.5 days), inactive slowest
            day_spacing = {
                "star": 1.5, "steady": 2.0, "improver": 2.5,
                "methodical": 2.5, "behind": 2.5, "inactive": 3.0,
            }
            spacing = day_spacing.get(personality, 2.0)
            start_time = enroll_time + timedelta(days=lab_idx * spacing + 1, hours=lab_idx % 8 + 9)
            completed_at = start_time + timedelta(minutes=time_spent)

            # Session record
            db.execute(text("""
                INSERT INTO lab_sessions (user_id, lab_id, status, started_at, expires_at, stopped_at)
                VALUES (:u, :l, 'stopped', :sa, :ea, :st)
            """), {
                "u": user_id, "l": lab["id"],
                "sa": start_time.isoformat(),
                "ea": (start_time + timedelta(hours=2)).isoformat(),
                "st": completed_at.isoformat(),
            })

            # Completion record
            flag_text = f"OCR{{{lab['slug'][:30]}}}"
            db.execute(text("""
                INSERT INTO lab_completions (user_id, lab_id, completed_at, flag_submitted,
                    attempts, hints_used, time_spent_minutes, started_at)
                VALUES (:u, :l, :ca, :fs, :att, :hu, :ts, :sa)
            """), {
                "u": user_id, "l": lab["id"],
                "ca": completed_at.isoformat(),
                "fs": flag_text,
                "att": attempts,
                "hu": hints_used,
                "ts": time_spent,
                "sa": start_time.isoformat(),
            })

            # Flag attempts — incorrect ones
            for attempt_num in range(1, attempts):
                attempt_time = start_time + timedelta(minutes=attempt_num * (time_spent // (attempts + 1)))
                db.execute(text("""
                    INSERT INTO flag_attempts (user_id, lab_id, flag_submitted, is_correct, attempted_at)
                    VALUES (:u, :l, :fs, false, :at)
                """), {
                    "u": user_id, "l": lab["id"],
                    "fs": f"wrong_flag_{attempt_num}",
                    "at": attempt_time.isoformat(),
                })
                log_event(db, "flag_incorrect", user_id, "lab", lab["id"],
                          lab["name"], created_at=attempt_time)

            # Hint requests
            for h in range(hints_used):
                hint_time = start_time + timedelta(minutes=5 + h * max(3, time_spent // 4))
                db.execute(text("""
                    INSERT INTO flag_attempts (user_id, lab_id, flag_submitted, is_correct, attempted_at)
                    VALUES (:u, :l, :fs, false, :at)
                """), {
                    "u": user_id, "l": lab["id"],
                    "fs": f"HINT_REQUEST_{h+1}",
                    "at": hint_time.isoformat(),
                })
                log_event(db, "hint_used", user_id, "lab", lab["id"],
                          lab["name"], created_at=hint_time)

            # Correct flag attempt
            db.execute(text("""
                INSERT INTO flag_attempts (user_id, lab_id, flag_submitted, is_correct, attempted_at)
                VALUES (:u, :l, :fs, true, :at)
            """), {
                "u": user_id, "l": lab["id"],
                "fs": flag_text,
                "at": completed_at.isoformat(),
            })

            # Activity events
            log_event(db, "lab_started", user_id, "lab", lab["id"],
                      lab["name"], created_at=start_time)
            log_event(db, "flag_correct", user_id, "lab", lab["id"],
                      lab["name"], created_at=completed_at)
            log_event(db, "lab_completed", user_id, "lab", lab["id"],
                      lab["name"], created_at=completed_at)

            # Track first_blood
            all_completions.append((user_id, lab["id"], completed_at, attempts, hints_used, time_ratio, lab))

            print(f"    [{lab_idx+1}] {lab['name'][:40]:40s} "
                  f"att={attempts} hints={hints_used} time={time_spent}m/{duration}m")

        db.commit()

    # ── 7. Award Achievements ────────────────────────────────
    print("\n[*] Awarding achievements...")

    # Determine first_blood per lab (earliest completion)
    first_blood_map = {}
    for uid, lab_id, completed_at, att, hints, tr, lab in all_completions:
        if lab_id not in first_blood_map or completed_at < first_blood_map[lab_id][1]:
            first_blood_map[lab_id] = (uid, completed_at)

    # Process achievements per student
    for s in STUDENTS:
        user_id = student_ids[s["username"]]["id"]
        personality = s["personality"]
        completed_labs = []

        for lab_idx, lab in enumerate(labs):
            attempts, hints_used, time_ratio, completed = get_profile(personality, lab_idx, len(labs))
            if not completed:
                continue

            completed_labs.append(lab_idx)
            duration = lab["duration"]
            enroll_offset = STUDENTS.index(s)
            enroll_time = course_start + timedelta(hours=enroll_offset * 4 + 2)
            spacing = {"star": 1.5, "steady": 2.0, "improver": 2.5,
                       "methodical": 2.5, "behind": 2.5, "inactive": 3.0}.get(personality, 2.0)
            completed_at = enroll_time + timedelta(
                days=lab_idx * spacing + 1,
                hours=lab_idx % 8 + 9,
                minutes=max(5, int(duration * time_ratio))
            )

            # First Blood
            if first_blood_map.get(lab["id"], (None,))[0] == user_id:
                award_achievement(db, user_id, course_id, lab["id"], "first_blood", completed_at)
                print(f"  {s['username']:20s} First Blood: {lab['name'][:35]}")

            # Self-Reliant (no hints)
            if hints_used == 0:
                award_achievement(db, user_id, course_id, lab["id"], "no_hints", completed_at)

            # Perfectionist (first attempt)
            if attempts == 1:
                award_achievement(db, user_id, course_id, lab["id"], "perfectionist", completed_at)

            # Speed Demon (under 50% time)
            if time_ratio < 0.5:
                award_achievement(db, user_id, course_id, lab["id"], "speed_demon", completed_at)

        # Clean Sweep (all labs completed)
        if len(completed_labs) == len(labs):
            award_achievement(db, user_id, course_id, None, "clean_sweep")
            print(f"  {s['username']:20s} Clean Sweep!")

        # Streak (3+ consecutive perfect: attempts==1, hints==0)
        streak_count = 0
        for lab_idx in completed_labs:
            att, hu, _, _ = get_profile(personality, lab_idx, len(labs))
            if att == 1 and hu == 0:
                streak_count += 1
            else:
                streak_count = 0
            if streak_count >= 3:
                award_achievement(db, user_id, course_id, None, "streak")
                print(f"  {s['username']:20s} On a Roll! (3+ perfect streak)")
                break

    db.commit()

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DEMO CLASS SEEDED SUCCESSFULLY")
    print("=" * 60)
    print(f"\n  Instructor Account:")
    print(f"    Username: {INSTRUCTOR['username']}")
    print(f"    Password: {INSTRUCTOR['password']}")
    print(f"    Role:     instructor")
    print(f"\n  Student Accounts (password for all: {PASSWORD}):")
    for s in STUDENTS:
        uid = student_ids[s["username"]]["id"]
        print(f"    {s['username']:20s} ({s['personality']:10s}) id={uid}")
    print(f"\n  Course: Cyber Security Fundamentals (CYB-3350)")
    print(f"    Course ID:   {course_id}")
    print(f"    Labs:        {len(labs)}")
    print(f"    Students:    {len(STUDENTS)}")
    print(f"    Invite Code: (check database)")
    print()


if __name__ == "__main__":
    seed_demo_class()
