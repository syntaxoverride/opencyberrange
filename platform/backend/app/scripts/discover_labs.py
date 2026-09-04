#!/usr/bin/env python3
"""
Lab Discovery Script
Scans the labs directory for lab.yaml files and populates the database
"""

import os
import sys
import re
import hashlib
import json

# Check for required dependencies before proceeding
_missing = []
for _mod in ['yaml', 'sqlalchemy']:
    try:
        __import__(_mod)
    except ImportError:
        _missing.append(_mod)

if _missing:
    print("Error: Missing required Python modules: " + ", ".join(_missing))
    print()
    print("This script is designed to run inside the Docker container, not directly on the host.")
    print()
    print("Run it using one of these methods:")
    print()
    print("  # Option 1: Execute inside the running backend container")
    print("  docker compose exec backend python /app/app/scripts/discover_labs.py")
    print()
    print("  # Option 2: Copy and run manually")
    print("  docker cp platform/scripts/discover_labs.py ocr-backend:/app/")
    print("  docker exec -it ocr-backend python3 /app/discover_labs.py")
    print()
    print("  # Option 3: Use the deployment script (re-discovers all labs)")
    print("  bash scripts/deploy-updates.sh --platform")
    sys.exit(1)

# Add the app directory to path
sys.path.insert(0, '/app')

import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://labuser:labpass@db:5432/labdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Labs directory (mounted in container)
LABS_DIR = os.environ.get('LABS_DIR', '/labs')


def parse_lab_slug(dirname):
    """Extract track, level, and lab number from directory name

    Examples:
        web-1-1-basic-directory-enumeration -> (web, 1, 1)
        web-2-1-basic-sql-injection-get -> (web, 2, 1)
        windows-1-1-basic-port-scan -> (windows, 1, 1)
        windows-8-1-single-service-credential-discovery -> (windows, 8, 1)
        windows-server-1-1-dc-port-discovery -> (windows-server, 1, 1)
        linux-midterm-3-blind-penetration-test -> (linux, None, 3)

    Supports compound track slugs: walks parts left-to-right, concatenating
    non-numeric parts as the track slug until the first numeric part (level).

    Midterm directories ({track}-midterm-{N}-...) return level_num=None and
    the midterm number as lab_num so callers can assign them without a level.
    """
    parts = dirname.split('-')
    if len(parts) < 3:
        return None, None, None

    # Build track slug by consuming non-numeric prefix parts
    track_parts = []
    i = 0
    while i < len(parts):
        # Check for pure numeric part (level number)
        try:
            int(parts[i])
            break  # Found first numeric part
        except ValueError:
            pass
        # Check for drill-style level like "D1", "D2" etc.
        drill_match = re.match(r'^[Dd](\d+)$', parts[i])
        if drill_match:
            break  # Treat D1, D2 etc. as the level indicator
        track_parts.append(parts[i].lower())
        i += 1

    if not track_parts or i + 1 >= len(parts):
        return None, None, None

    # Handle midterm and final directories: {track}-{midterm|final}-{N}-{description}
    # Both share the level=None pattern so they exist outside the regular level
    # progression. lab_num for finals is offset by 500 to avoid collision with
    # midterm lab_nums in the same track.
    if track_parts[-1] in ('midterm', 'final'):
        base_track = '-'.join(track_parts[:-1])
        if not base_track:
            return None, None, None
        try:
            special_num = int(parts[i])
            if track_parts[-1] == 'final':
                special_num = 500 + special_num
            return base_track, None, special_num
        except (ValueError, IndexError):
            return None, None, None

    track_slug = '-'.join(track_parts)
    try:
        # Handle drill-style levels (D1 -> level 901, D2 -> 902, etc.)
        drill_match = re.match(r'^[Dd](\d+)$', parts[i])
        if drill_match:
            level_num = 900 + int(drill_match.group(1))
        else:
            level_num = int(parts[i])
        lab_num = int(parts[i + 1])
        return track_slug, level_num, lab_num
    except (ValueError, IndexError):
        return None, None, None


def hash_flag(flag):
    """Create SHA256 hash of flag for storage"""
    return hashlib.sha256(flag.encode()).hexdigest()






import re

# Characters that cause shell quoting failures through the tester exec chain
_DANGEROUS_PW_CHARS = set('!`$\\"')

def _validate_lab_quick(lab_path, lab_data):
    """Run critical validation checks inline. Returns (status, errors_json).

    status: "ok" | "warning" | "error"
    errors_json: JSON string of [{name, passed, message, severity}]
    """
    issues = []

    # 1. Password safety in credentials
    for cred in lab_data.get("credentials", []):
        pw = cred.get("password", "")
        role = cred.get("role", "?")
        bad = [c for c in pw if c in _DANGEROUS_PW_CHARS]
        if bad:
            issues.append({
                "name": f"Password safe ({role})",
                "passed": False,
                "message": f"Password for '{role}' contains {' '.join(repr(c) for c in bad)} -- will break through shell layers",
                "severity": "error"
            })

    # 2. Command anti-patterns in test steps
    for step in lab_data.get("test", {}).get("steps", []):
        cmd = step.get("command", "")
        name = step.get("name", "unnamed")
        if re.search(r"-X\s+POST", cmd) and "-L" in cmd:
            issues.append({
                "name": f"-X POST + -L ({name})",
                "passed": False,
                "message": "curl -X POST + -L causes 405 on redirects. Remove -X POST.",
                "severity": "error"
            })
        if re.search(r"grep\s+(-\w*P|--perl-regexp)", cmd):
            issues.append({
                "name": f"grep -P ({name})",
                "passed": False,
                "message": "grep -P not portable to Alpine/BusyBox. Use grep -o + cut.",
                "severity": "warning"
            })
        if "!=" in cmd and ("jq" in cmd or "select" in cmd):
            issues.append({
                "name": f"!= in jq ({name})",
                "passed": False,
                "message": "!= risks bash history expansion. Use select(.field) instead.",
                "severity": "error"
            })

    # 3. Template variable resolution
    node_ids = {n.get("id") for n in lab_data.get("topology", {}).get("nodes", []) if n.get("id")}
    compose_path = os.path.join(lab_path, "docker-compose.yml")
    if os.path.exists(compose_path):
        try:
            with open(compose_path, "r") as f:
                comp = yaml.safe_load(f) or {}
            for svc in comp.get("services", {}).keys():
                node_ids.add(svc)
        except Exception:
            pass
    cred_roles = {c.get("role") for c in lab_data.get("credentials", []) if c.get("role")}

    for step in lab_data.get("test", {}).get("steps", []):
        cmd = step.get("command", "")
        name = step.get("name", "unnamed")
        for m in re.finditer(r"\{target\.([^}]+)\}", cmd):
            if m.group(1) not in node_ids:
                issues.append({
                    "name": f"{{target.{m.group(1)}}} ({name})",
                    "passed": False,
                    "message": f"No matching topology node or compose service '{m.group(1)}'",
                    "severity": "error"
                })
        for m in re.finditer(r"\{cred\.([^.}]+)\.(user|pass)\}", cmd):
            if m.group(1) not in cred_roles:
                issues.append({
                    "name": f"{{cred.{m.group(1)}.{m.group(2)}}} ({name})",
                    "passed": False,
                    "message": f"No credential with role '{m.group(1)}'",
                    "severity": "error"
                })

    # 4. MySQL auth plugin check
    for root, dirs, files in os.walk(lab_path):
        for f in files:
            fpath = os.path.join(root, f)
            _, ext = os.path.splitext(f)
            if f in ("Dockerfile", "docker-compose.yml"):
                try:
                    with open(fpath, "r", errors="ignore") as fh:
                        content = fh.read()
                    if "mysql:8" in content.lower() or "mysql:latest" in content.lower():
                        # Scan for CREATE USER without mysql_native_password
                        for sf in files:
                            sfpath = os.path.join(root, sf)
                            sfext = os.path.splitext(sf)[1].lower()
                            if sfext in (".sql", "") or sf == "Dockerfile":
                                try:
                                    with open(sfpath, "r", errors="ignore") as sfh:
                                        sc = sfh.read()
                                    if re.search(r"CREATE\s+USER.*IDENTIFIED\s+BY\s+", sc, re.I):
                                        if not re.search(r"IDENTIFIED\s+WITH\s+mysql_native_password", sc, re.I):
                                            rel = os.path.relpath(sfpath, lab_path)
                                            issues.append({
                                                "name": f"MySQL auth ({rel})",
                                                "passed": False,
                                                "message": "MySQL 8 user without mysql_native_password -- mariadb-client won't connect",
                                                "severity": "error"
                                            })
                                except IOError:
                                    pass
                except IOError:
                    pass

    # Determine overall status
    has_errors = any(i["severity"] == "error" for i in issues)
    has_warnings = any(i["severity"] == "warning" for i in issues)
    if has_errors:
        status = "error"
    elif has_warnings:
        status = "warning"
    else:
        status = "ok"

    return status, json.dumps(issues) if issues else None


def discover_labs():
    """Scan labs directory and populate database"""
    db = SessionLocal()
    
    try:
        # Ensure validation columns exist (idempotent migration)
        for col, coltype in [
            ("validation_status", "VARCHAR(20)"),
            ("validation_errors", "TEXT"),
            ("validated_at", "TIMESTAMP"),
            ("requires_kvm", "BOOLEAN DEFAULT FALSE"),
        ]:
            try:
                db.execute(text(f"ALTER TABLE labs ADD COLUMN {col} {coltype}"))  # sql-safe: DDL; col/coltype from the constant allowlist above (identifiers can't be bound params)
                db.commit()
            except Exception:
                db.rollback()  # Column already exists

        # Get all tracks and levels
        tracks = {}
        levels = {}
        
        track_rows = db.execute(text("SELECT id, slug FROM tracks")).fetchall()
        for row in track_rows:
            tracks[row[1]] = row[0]
        
        level_rows = db.execute(text("SELECT id, track_id, level_number FROM levels")).fetchall()
        for row in level_rows:
            # Key by (track_id, level_number)
            levels[(row[1], row[2])] = row[0]
        
        print(f"Found {len(tracks)} tracks and {len(levels)} levels")
        print(f"Tracks: {list(tracks.keys())}")
        
        if not os.path.exists(LABS_DIR):
            print(f"Labs directory not found: {LABS_DIR}")
            return
        
        labs_created = 0
        labs_updated = 0
        
        # Scan each track directory
        for track_name in os.listdir(LABS_DIR):
            track_path = os.path.join(LABS_DIR, track_name)
            # Skip hidden and underscore-prefixed dirs (_archive, _pending, etc.)
            if not os.path.isdir(track_path) or track_name[:1] in ('.', '_'):
                continue

            print(f"\nScanning track directory: {track_name}")

            # Scan each lab directory
            for lab_dirname in sorted(os.listdir(track_path)):
                lab_path = os.path.join(track_path, lab_dirname)
                # Underscore prefix (e.g. _archive-*) marks a retired/disabled lab.
                if not os.path.isdir(lab_path) or lab_dirname[:1] in ('.', '_'):
                    continue
                
                yaml_path = os.path.join(lab_path, 'lab.yaml')
                compose_path = os.path.join(lab_path, 'docker-compose.yml')
                
                if not os.path.exists(yaml_path):
                    print(f"  Skipping {lab_dirname}: no lab.yaml")
                    continue
                
                # Parse lab info from directory name
                track_slug, level_num, lab_num = parse_lab_slug(lab_dirname)
                
                if not track_slug:
                    print(f"  Skipping {lab_dirname}: can't parse directory name")
                    continue
                
                # Find track and level
                track_id = tracks.get(track_slug)
                if not track_id:
                    print(f"  Skipping {lab_dirname}: track '{track_slug}' not found")
                    continue

                # Midterm labs (level_num=None) have no level assignment
                # Drill labs (level_num >= 900) map to their base level with offset sort_order
                is_drill = level_num is not None and level_num >= 900
                if is_drill:
                    base_level = level_num - 900
                    level_id = levels.get((track_id, base_level))
                    if not level_id:
                        print(f"  Skipping {lab_dirname}: base level {base_level} not found in track '{track_slug}'")
                        continue
                    # Offset sort_order so drills appear after main exercises
                    lab_num = 100 + lab_num
                elif level_num is not None:
                    level_id = levels.get((track_id, level_num))
                    if not level_id:
                        print(f"  Skipping {lab_dirname}: level {level_num} not found in track '{track_slug}'")
                        continue
                else:
                    level_id = None
                
                # Load lab.yaml
                try:
                    with open(yaml_path, 'r') as f:
                        lab_data = yaml.safe_load(f)
                except Exception as e:
                    print(f"  Error reading {yaml_path}: {e}")
                    continue
                
                # Load docker-compose.yml if exists
                compose_content = ""
                if os.path.exists(compose_path):
                    try:
                        with open(compose_path, 'r') as f:
                            compose_content = f.read()
                    except Exception as e:
                        print(f"  Warning: can't read docker-compose.yml: {e}")

                # Labs whose compose declares an external container need the
                # Windows VM, which needs /dev/kvm on the host
                requires_kvm = False
                if compose_content:
                    try:
                        _comp = yaml.safe_load(compose_content) or {}
                        requires_kvm = bool(_comp.get('x-ocr-shared-containers'))
                    except Exception:
                        requires_kvm = False
                
                # Prepare lab data
                lab_slug = lab_dirname
                lab_name = lab_data.get('name', lab_dirname)
                description = lab_data.get('description', '')
                scenario = lab_data.get('scenario', '')
                scenario_brief = lab_data.get('scenario_brief', '')
                if not scenario_brief and scenario:
                    scenario_brief = scenario[:150] + '...' if len(scenario) > 150 else scenario
                
                difficulty = lab_data.get('difficulty', 'beginner')
                category = lab_data.get('category', 'general')
                duration = lab_data.get('duration_minutes', 60)
                
                objectives = json.dumps(lab_data.get('objectives', []))
                hints_raw = lab_data.get('hints', [])
                hints = json.dumps(hints_raw)
                tools = json.dumps(lab_data.get('tools', []))
                hostnames = json.dumps(lab_data.get('hostnames', []))
                workbook = lab_data.get('workbook', None)
                show_target_ips = bool(lab_data.get('show_target_ips', False))
                # Extract topology nodes (id, label, ip_offset) for target IP display
                topo_raw = lab_data.get('topology', {}).get('nodes', [])
                topology_nodes = json.dumps([
                    {"id": n.get("id", ""), "label": n.get("label", ""), "ip_offset": n.get("ip_offset", "")}
                    for n in topo_raw if n.get("ip_offset")
                ]) if topo_raw else None
                # ICS attack-coverage tags (list of {tactic, technique_id, technique_name, note})
                ics_techniques = json.dumps(lab_data.get('ics_techniques', [])) if lab_data.get('ics_techniques') else None
                week = lab_data.get('week', None) or lab_data.get('phase', None)
                if week is not None:
                    try:
                        week = int(week)
                    except (ValueError, TypeError):
                        week = None

                # Read initial visibility for new labs (existing labs keep their DB value)
                yaml_visibility = lab_data.get('visibility', 'public')
                if yaml_visibility not in ('draft', 'course', 'public'):
                    yaml_visibility = 'public'

                # Debug: Print hint count
                if hints_raw:
                    print(f"    Found {len(hints_raw)} hints for {lab_name}")
                
                # Hash flag if present
                flag = lab_data.get('flag', '')
                flag_hash = hash_flag(flag) if flag else None

                # Run inline validation
                val_status, val_errors = _validate_lab_quick(lab_path, lab_data)
                from datetime import datetime as _dt
                val_at = _dt.utcnow()
                if val_status != "ok":
                    issue_count = len(json.loads(val_errors)) if val_errors else 0
                    print(f"    Validation: {val_status.upper()} ({issue_count} issue(s))")

                # Check if lab exists
                existing = db.execute(
                    text("SELECT id FROM labs WHERE slug = :slug"),
                    {"slug": lab_slug}
                ).fetchone()
                
                if existing:
                    # Update existing lab
                    # Build update parameters - always update flag_hash when provided
                    update_params = {
                        "name": lab_name,
                        "description": description,
                        "scenario": scenario,
                        "scenario_brief": scenario_brief,
                        "difficulty": difficulty,
                        "category": category,
                        "duration": duration,
                        "objectives": objectives,
                        "hints": hints,
                        "tools": tools,
                        "hostnames": hostnames,
                        "compose_file": compose_content,
                        "level_id": level_id,
                        "sort_order": lab_num,
                        "slug": lab_slug,
                        "workbook": workbook,
                        "week": week,
                        "show_target_ips": show_target_ips,
                        "topology_nodes": topology_nodes,
                        "ics_techniques": ics_techniques,
                        "requires_kvm": requires_kvm,
                        "validation_status": val_status,
                        "validation_errors": val_errors,
                        "validated_at": val_at,
                    }

                    # Always update flag_hash when provided (not None)
                    if flag_hash is not None:
                        update_sql = """
                            UPDATE labs SET
                                name = :name,
                                description = :description,
                                scenario = :scenario,
                                scenario_brief = :scenario_brief,
                                difficulty = :difficulty,
                                category = :category,
                                duration_minutes = :duration,
                                objectives = :objectives,
                                hints = :hints,
                                tools = :tools,
                                hostnames = :hostnames,
                                flag_hash = :flag_hash,
                                compose_file = :compose_file,
                                level_id = :level_id,
                                sort_order = :sort_order,
                                workbook = :workbook,
                                week = :week,
                                show_target_ips = :show_target_ips,
                                topology_nodes = :topology_nodes,
                                ics_techniques = :ics_techniques,
                                requires_kvm = :requires_kvm,
                                validation_status = :validation_status,
                                validation_errors = :validation_errors,
                                validated_at = :validated_at
                            WHERE slug = :slug
                        """
                        update_params["flag_hash"] = flag_hash
                    else:
                        # Keep existing flag_hash if not provided
                        update_sql = """
                            UPDATE labs SET
                                name = :name,
                                description = :description,
                                scenario = :scenario,
                                scenario_brief = :scenario_brief,
                                difficulty = :difficulty,
                                category = :category,
                                duration_minutes = :duration,
                                objectives = :objectives,
                                hints = :hints,
                                tools = :tools,
                                hostnames = :hostnames,
                                compose_file = :compose_file,
                                level_id = :level_id,
                                sort_order = :sort_order,
                                workbook = :workbook,
                                week = :week,
                                show_target_ips = :show_target_ips,
                                topology_nodes = :topology_nodes,
                                ics_techniques = :ics_techniques,
                                requires_kvm = :requires_kvm,
                                validation_status = :validation_status,
                                validation_errors = :validation_errors,
                                validated_at = :validated_at
                            WHERE slug = :slug
                        """
                    
                    db.execute(
                        text(update_sql),
                        update_params
                    )
                    print(f"  ✓ Updated: {lab_name}")
                    labs_updated += 1
                else:
                    # Insert new lab
                    db.execute(
                        text("""
                            INSERT INTO labs (
                                name, slug, description, scenario, scenario_brief,
                                difficulty, category, duration_minutes, objectives,
                                hints, tools, hostnames,
                                flag_hash, compose_file, level_id, sort_order, is_active,
                                visibility, workbook, week, show_target_ips, topology_nodes,
                                ics_techniques, requires_kvm,
                                validation_status, validation_errors, validated_at
                            ) VALUES (
                                :name, :slug, :description, :scenario, :scenario_brief,
                                :difficulty, :category, :duration, :objectives,
                                :hints, :tools, :hostnames,
                                :flag_hash, :compose_file, :level_id, :sort_order, TRUE,
                                :visibility, :workbook, :week, :show_target_ips, :topology_nodes,
                                :ics_techniques, :requires_kvm,
                                :validation_status, :validation_errors, :validated_at
                            )
                        """),
                        {
                            "name": lab_name,
                            "slug": lab_slug,
                            "description": description,
                            "scenario": scenario,
                            "scenario_brief": scenario_brief,
                            "difficulty": difficulty,
                            "category": category,
                            "duration": duration,
                            "objectives": objectives,
                            "hints": hints,
                            "tools": tools,
                            "hostnames": hostnames,
                            "flag_hash": flag_hash,
                            "compose_file": compose_content,
                            "level_id": level_id,
                            "sort_order": lab_num,
                            "visibility": yaml_visibility,
                            "workbook": workbook,
                            "week": week,
                            "show_target_ips": show_target_ips,
                            "topology_nodes": topology_nodes,
                                "ics_techniques": ics_techniques,
                            "requires_kvm": requires_kvm,
                            "validation_status": val_status,
                            "validation_errors": val_errors,
                            "validated_at": val_at,
                        }
                    )
                    print(f"  ✓ Created: {lab_name}")
                    labs_created += 1
        
        db.commit()

        # Validation summary
        val_rows = db.execute(
            text("SELECT validation_status, COUNT(*) FROM labs GROUP BY validation_status")
        ).fetchall()
        val_summary = {row[0]: row[1] for row in val_rows}

        print(f"\n========================================")
        print(f"Lab discovery complete!")
        print(f"  Created: {labs_created}")
        print(f"  Updated: {labs_updated}")
        if val_summary:
            print(f"  Validation: {val_summary.get('ok', 0)} ok, "
                  f"{val_summary.get('warning', 0)} warnings, "
                  f"{val_summary.get('error', 0)} errors")
        print(f"========================================")
        
    except Exception as e:
        db.rollback()
        print(f"Error discovering labs: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def sync_course_week_assignments():
    """Auto-create 'Week N' assignments for courses that have week-tagged labs.

    For each active (non-archived) course:
    1. Find all labs assigned to the course that have a week value.
    2. For each unique week number, ensure an Assignment named 'Week N' exists.
    3. Link each lab to its week assignment via AssignmentLab.

    This is idempotent — running it multiple times won't duplicate data.
    """
    db = SessionLocal()
    try:
        # Find all active courses
        courses = db.execute(
            text("SELECT id, name FROM courses WHERE is_archived = FALSE")
        ).fetchall()

        if not courses:
            print("\nNo active courses — skipping week assignment sync.")
            return

        for course_id, course_name in courses:
            # Skip courses that have manually-created assignments (names that
            # don't match the auto-generated "Phase N" pattern).  If an
            # instructor built their own assignment structure, we should not
            # inject Phase assignments into it.
            manual = db.execute(
                text("""
                    SELECT COUNT(*) FROM assignments
                    WHERE course_id = :course_id
                      AND name !~ '^Phase [0-9]+$'
                """),
                {"course_id": course_id}
            ).scalar()
            if manual:
                print(f"\nSkipping course '{course_name}' — has {manual} manually-created assignment(s)")
                continue

            # Get all labs assigned to this course that have a week value
            week_labs = db.execute(
                text("""
                    SELECT cla.lab_id, l.week, l.name
                    FROM course_lab_assignments cla
                    JOIN labs l ON l.id = cla.lab_id
                    WHERE cla.course_id = :course_id
                      AND l.week IS NOT NULL
                    ORDER BY l.week
                """),
                {"course_id": course_id}
            ).fetchall()

            if not week_labs:
                continue

            print(f"\nSyncing week assignments for course: {course_name}")

            # Get existing assignments for this course keyed by name
            existing_assignments = {}
            rows = db.execute(
                text("SELECT id, name FROM assignments WHERE course_id = :course_id"),
                {"course_id": course_id}
            ).fetchall()
            for row in rows:
                existing_assignments[row[1]] = row[0]

            # Get existing assignment_labs for this course (to avoid duplicates)
            existing_assignment_labs = set()
            if existing_assignments:
                al_rows = db.execute(
                    text("""
                        SELECT al.assignment_id, al.lab_id
                        FROM assignment_labs al
                        JOIN assignments a ON a.id = al.assignment_id
                        WHERE a.course_id = :course_id
                    """),
                    {"course_id": course_id}
                ).fetchall()
                for row in al_rows:
                    existing_assignment_labs.add((row[0], row[1]))

            assignments_created = 0
            labs_linked = 0

            for lab_id, week_num, lab_name in week_labs:
                assignment_name = f"Phase {week_num}"

                # Create assignment if it doesn't exist
                if assignment_name not in existing_assignments:
                    db.execute(
                        text("""
                            INSERT INTO assignments (course_id, name, sort_order)
                            VALUES (:course_id, :name, :sort_order)
                        """),
                        {"course_id": course_id, "name": assignment_name, "sort_order": week_num}
                    )
                    db.flush()
                    # Fetch the new assignment id
                    new_id = db.execute(
                        text("SELECT id FROM assignments WHERE course_id = :course_id AND name = :name"),
                        {"course_id": course_id, "name": assignment_name}
                    ).fetchone()[0]
                    existing_assignments[assignment_name] = new_id
                    assignments_created += 1
                    print(f"  + Created assignment: {assignment_name}")

                assignment_id = existing_assignments[assignment_name]

                # Link lab to assignment if not already linked
                if (assignment_id, lab_id) not in existing_assignment_labs:
                    db.execute(
                        text("""
                            INSERT INTO assignment_labs (assignment_id, lab_id, sort_order)
                            VALUES (:assignment_id, :lab_id, :sort_order)
                        """),
                        {"assignment_id": assignment_id, "lab_id": lab_id, "sort_order": 1}
                    )
                    existing_assignment_labs.add((assignment_id, lab_id))
                    labs_linked += 1
                    print(f"    → Linked '{lab_name}' to {assignment_name}")

            if assignments_created or labs_linked:
                print(f"  Summary: {assignments_created} assignments created, {labs_linked} labs linked")

        db.commit()
        print("\nWeek assignment sync complete!")

    except Exception as e:
        db.rollback()
        print(f"Error syncing week assignments: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    discover_labs()
    sync_course_week_assignments()

