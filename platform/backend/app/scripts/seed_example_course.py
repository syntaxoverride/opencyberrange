#!/usr/bin/env python3
"""
Example Course Seed Script
Creates a "Penetration Testing" example course with pre-assigned exercises.
No users are created — the course will be assigned to the first admin/instructor
who runs the platform setup.

Run inside Docker:
  docker compose exec backend python /app/app/scripts/seed_example_course.py
"""

import os
import sys
import secrets

_missing = []
for _mod in ['sqlalchemy']:
    try:
        __import__(_mod)
    except ImportError:
        _missing.append(_mod)

if _missing:
    print("Error: Missing required Python modules: " + ", ".join(_missing))
    print("This script runs inside the Docker container:")
    print("  docker compose exec backend python /app/app/scripts/seed_example_course.py")
    sys.exit(1)

sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://labuser:labpass@db:5432/labdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Course definition
COURSE = {
    "name": "Penetration Testing",
    "code": "SEC 400",
    "description": "A comprehensive penetration testing course covering Windows, Linux, Web, and Network attack techniques. Students progress from reconnaissance through full exploitation across multiple platforms.",
}

# Exercises assigned to the course, in order
COURSE_LABS = [
    # Windows Track Foundation
    "windows-1-1-basic-port-scan",
    "windows-1-2-multiple-port-discovery",
    "windows-1-3-windows-service-version-detection",
    "windows-1-4-windows-os-detection",
    "windows-1-5-comprehensive-windows-enumeration",
    "windows-10-1-network-enumeration-assessment",
    "windows-10-2-midterm-assessment",
    # Week 1 — Network Discovery
    "linux-1-7-network-discovery",
    "linux-1-8-service-triage",
    # Week 2 — SMB Enumeration
    "linux-2-7-smb-share-enumeration",
    "linux-2-9-smb-credential-hunt",
    # Week 3 — SNMP
    "linux-2-8-snmp-community-strings",
    "linux-2-10-snmp-breadcrumb-trail",
    # Week 4 — Directory Traversal
    "web-1-7-directory-traversal",
    "web-1-8-traversal-scavenger-hunt",
    # Week 5 — Insecure APIs
    "web-2-2-insecure-api-endpoints",
    "web-2-4-api-enumeration-gauntlet",
    # Week 6 — Command Injection
    "web-2-3-command-injection",
    "web-2-5-filtered-injection",
    # Week 7 — SUID Privilege Escalation
    "linux-3-1-suid-privilege-escalation",
    "linux-3-3-suid-maze",
    # Week 8 — Password Hash Cracking
    "linux-3-2-password-hash-cracking",
    "linux-3-4-hash-relay",
    # Week 9 — Midterm
    "linux-midterm-2-full-penetration-test",
    "linux-midterm-3-blind-penetration-test",
    # Week 10 — Hidden Login / SQL Injection
    "web-3-1-hidden-login-discovery",
    "web-3-2-sql-injection-to-shell",
    "web-3-3-full-web-to-root",
    # Week 11 — Credential Pivoting
    "linux-4-1-credential-pivot-attack",
    "linux-4-3-three-hop-pivot",
    # Week 12 — Post-Exploitation
    "linux-4-2-post-exploitation-data-harvest",
    "linux-4-4-encrypted-exfiltration",
    # Week 13 — Packet Capture / Log Correlation
    "network-1-1-packet-capture-analysis",
    "network-1-2-log-correlation",
    # Week 14 — IDS Detection
    "linux-5-4-suricata-live-detection",
    "linux-5-6-brute-force-detection",
    # Week 15 — Capstone
    "linux-5-5-capstone-ctf",
    "linux-5-7-black-box-ctf",
]


def seed_example_course():
    db = SessionLocal()
    try:
        # Check if course already exists
        existing = db.execute(
            text("SELECT id FROM courses WHERE code = :code"),
            {"code": COURSE["code"]}
        ).fetchone()

        if existing:
            course_id = existing[0]
            print(f"Course '{COURSE['code']}' already exists (id={course_id}). Syncing lab assignments...")

            # Sync: add any missing labs and update sort_order for all
            labs_added = 0
            labs_updated = 0
            labs_missing = 0
            for sort_order, slug in enumerate(COURSE_LABS, start=1):
                lab = db.execute(
                    text("SELECT id, name FROM labs WHERE slug = :slug"),
                    {"slug": slug}
                ).fetchone()

                if not lab:
                    print(f"  ⚠ Lab not found: {slug} (run discover_labs.py first)")
                    labs_missing += 1
                    continue

                assigned = db.execute(
                    text("SELECT id FROM course_lab_assignments WHERE course_id = :cid AND lab_id = :lid"),
                    {"cid": course_id, "lid": lab[0]}
                ).fetchone()

                if assigned:
                    db.execute(
                        text("UPDATE course_lab_assignments SET sort_order = :so WHERE id = :id"),
                        {"so": sort_order, "id": assigned[0]}
                    )
                    labs_updated += 1
                else:
                    db.execute(
                        text("INSERT INTO course_lab_assignments (course_id, lab_id, sort_order) VALUES (:cid, :lid, :so)"),
                        {"cid": course_id, "lid": lab[0], "so": sort_order}
                    )
                    print(f"  ✓ Added [{sort_order:2d}]: {lab[1]}")
                    labs_added += 1

            db.commit()
            print(f"\n✓ Sync complete! Added: {labs_added}, Updated: {labs_updated}")
            if labs_missing:
                print(f"  Labs missing: {labs_missing} (run discover_labs.py to populate)")
            return

        # Find the first admin user to assign as instructor (or NULL if none yet)
        admin = db.execute(
            text("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
        ).fetchone()
        instructor_id = admin[0] if admin else None

        if not instructor_id:
            print("No admin user found yet. Course will be created without an instructor.")
            print("The first admin created via /setup will need to be assigned manually,")
            print("or re-run this script after setup completes.")

        # Create the course
        invite_code = secrets.token_urlsafe(6)
        result = db.execute(
            text("""
                INSERT INTO courses (name, code, description, instructor_id, invite_code,
                                     semester, start_date, end_date, is_active, is_archived)
                VALUES (:name, :code, :description, :instructor_id, :invite_code,
                        :semester, NOW(), NOW() + INTERVAL '120 days', TRUE, FALSE)
                RETURNING id
            """),
            {
                "name": COURSE["name"],
                "code": COURSE["code"],
                "description": COURSE["description"],
                "instructor_id": instructor_id,
                "invite_code": invite_code,
                "semester": "Example Term",
            }
        )
        course_id = result.fetchone()[0]
        print(f"✓ Created course: {COURSE['name']} ({COURSE['code']}) [id={course_id}]")
        print(f"  Invite code: {invite_code}")

        # Assign labs to course
        labs_assigned = 0
        labs_missing = 0
        for sort_order, slug in enumerate(COURSE_LABS, start=1):
            lab = db.execute(
                text("SELECT id, name FROM labs WHERE slug = :slug"),
                {"slug": slug}
            ).fetchone()

            if not lab:
                print(f"  ⚠ Lab not found: {slug} (run discover_labs.py first)")
                labs_missing += 1
                continue

            db.execute(
                text("""
                    INSERT INTO course_lab_assignments (course_id, lab_id, sort_order)
                    VALUES (:course_id, :lab_id, :sort_order)
                """),
                {"course_id": course_id, "lab_id": lab[0], "sort_order": sort_order}
            )
            print(f"  ✓ Assigned [{sort_order:2d}]: {lab[1]}")
            labs_assigned += 1

        db.commit()
        print(f"\n✓ Example course seeding complete!")
        print(f"  Labs assigned: {labs_assigned}")
        if labs_missing:
            print(f"  Labs missing:  {labs_missing} (run discover_labs.py to populate)")

    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding example course: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_example_course()
