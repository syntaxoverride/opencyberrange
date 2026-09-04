#!/usr/bin/env python3
"""
Lab Discovery Script
Scans the labs directory for lab.yaml files and populates the database
"""

import os
import sys
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
    
    Directory names directly reflect level numbers (1-9 for Windows track)
    """
    parts = dirname.split('-')
    if len(parts) >= 3:
        track_slug = parts[0].lower()
        try:
            level_num = int(parts[1])
            lab_num = int(parts[2])
            
            # No mapping needed - directory names use correct level numbers
            return track_slug, level_num, lab_num
        except ValueError:
            pass
    return None, None, None


def hash_flag(flag):
    """Create SHA256 hash of flag for storage"""
    return hashlib.sha256(flag.encode()).hexdigest()


def discover_labs():
    """Scan labs directory and populate database"""
    db = SessionLocal()
    
    try:
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
            if not os.path.isdir(track_path) or track_name.startswith('.'):
                continue
            
            print(f"\nScanning track directory: {track_name}")
            
            # Scan each lab directory
            for lab_dirname in sorted(os.listdir(track_path)):
                lab_path = os.path.join(track_path, lab_dirname)
                if not os.path.isdir(lab_path) or lab_dirname.startswith('.'):
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
                
                level_id = levels.get((track_id, level_num))
                if not level_id:
                    print(f"  Skipping {lab_dirname}: level {level_num} not found in track '{track_slug}'")
                    continue
                
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
                        "workbook": workbook
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
                                workbook = :workbook
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
                                workbook = :workbook
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
                                visibility, workbook
                            ) VALUES (
                                :name, :slug, :description, :scenario, :scenario_brief,
                                :difficulty, :category, :duration, :objectives,
                                :hints, :tools, :hostnames,
                                :flag_hash, :compose_file, :level_id, :sort_order, TRUE,
                                :visibility, :workbook
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
                            "workbook": workbook
                        }
                    )
                    print(f"  ✓ Created: {lab_name}")
                    labs_created += 1
        
        db.commit()
        print(f"\n========================================")
        print(f"Lab discovery complete!")
        print(f"  Created: {labs_created}")
        print(f"  Updated: {labs_updated}")
        print(f"========================================")
        
    except Exception as e:
        db.rollback()
        print(f"Error discovering labs: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    discover_labs()

