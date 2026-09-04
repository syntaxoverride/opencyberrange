#!/usr/bin/env python3
"""Seed the edition's prebuilt sample class(es).

Each pack may declare a `prebuilt_class` in the edition manifest; the build
writes those into data/prebuilt_class.json as a list of
  {name, code, description, track_slug}.

For every entry, this creates a course from the named track's labs (assigned as
course_lab_assignments, in track order) owned by the given instructor. It runs
at setup-complete, once the first admin exists -- courses.instructor_id is
NOT NULL, so there is no such thing as an ownerless course.

Idempotent: a course whose `code` already exists is skipped.

Importable:  seed_prebuilt_class(db, instructor_id)
CLI (inside the backend container):  python -m app.scripts.seed_prebuilt_class <instructor_id>
"""
import os
import sys
import json
import secrets
from datetime import datetime, timedelta

sys.path.insert(0, '/app')

from sqlalchemy import text


def _defs_path() -> str:
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(app_root, 'data', 'prebuilt_class.json')


def seed_prebuilt_class(db, instructor_id: int):
    """Create any declared prebuilt classes owned by instructor_id.

    Returns the list of course codes created (empty if none / already present)."""
    path = _defs_path()
    if not os.path.exists(path):
        return []
    try:
        defs = json.load(open(path))
    except Exception:
        return []
    if not isinstance(defs, list):
        return []

    created = []
    for d in defs:
        code = (d or {}).get('code')
        name = (d or {}).get('name')
        track_slug = (d or {}).get('track_slug')
        if not (code and name and track_slug):
            continue

        # Idempotent on course code.
        if db.execute(text("SELECT id FROM courses WHERE code = :c"), {"c": code}).first():
            continue

        track = db.execute(text("SELECT id FROM tracks WHERE slug = :s"), {"s": track_slug}).first()
        if not track:
            continue
        track_id = track[0]

        # labs link to a track through levels (labs.level_id -> levels.track_id).
        labs = db.execute(text(
            "SELECT l.id FROM labs l JOIN levels lv ON l.level_id = lv.id "
            "WHERE lv.track_id = :t "
            "ORDER BY lv.level_number, COALESCE(lv.sort_order, 0), COALESCE(l.sort_order, 0), l.id"
        ), {"t": track_id}).fetchall()
        if not labs:
            continue

        # courses requires name, code, semester, invite_code, instructor_id,
        # start_date, end_date (all NOT NULL, no default). invite_code is UNIQUE.
        now = datetime.utcnow()
        course = db.execute(text(
            "INSERT INTO courses "
            "(name, code, description, semester, instructor_id, invite_code, "
            " start_date, end_date, is_active, is_archived) "
            "VALUES (:name, :code, :desc, :sem, :inst, :invite, :start, :end, TRUE, FALSE) "
            "RETURNING id"
        ), {
            "name": name[:150],
            "code": code[:20],
            "desc": d.get('description') or f"Sample class pre-loaded from the {name} track. Edit or archive it as you like.",
            "sem": "Self-paced",
            "inst": instructor_id,
            "invite": secrets.token_hex(4),
            "start": now,
            "end": now + timedelta(days=120),
        }).first()
        course_id = course[0]

        for sort_order, lab in enumerate(labs):
            db.execute(text(
                "INSERT INTO course_lab_assignments (course_id, lab_id, sort_order) "
                "VALUES (:c, :l, :so)"
            ), {"c": course_id, "l": lab[0], "so": sort_order})

        db.commit()
        created.append(code)

    return created


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if len(sys.argv) < 2:
        print("usage: python -m app.scripts.seed_prebuilt_class <instructor_id>")
        sys.exit(1)
    inst_id = int(sys.argv[1])

    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://labuser:labpass@db:5432/labdb')
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        made = seed_prebuilt_class(db, inst_id)
        print(f"Prebuilt classes created: {made}" if made
              else "No prebuilt classes to create (none declared, track empty, or already present).")
    finally:
        db.close()
