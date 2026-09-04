#!/usr/bin/env python3
"""
Targeted seed for the Network Defense (netdef) track only.

Registers the netdef track and its five levels so discover_labs can import
the 10 NetDef exercises. Idempotent: updates the track/levels if they already
exist, creates them otherwise. Deliberately scoped to netdef so it does not
touch other tracks (running the full seed_curriculum would overwrite track
icons/colors that were customized live).

Run inside the backend container:
    python3 -m app.scripts.seed_netdef
"""
import os
import sys

sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://labuser:labpass@db:5432/labdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TRACK = {
    "name": "Network Defense",
    "slug": "netdef",
    "description": (
        "Defend Arcline Systems, an autonomous-vehicle AI company, as a SOC "
        "analyst across a five-segment network. Detect, investigate, and "
        "remediate threats using Cisco-style FRR routing, Suricata IDS, and "
        "network segmentation, progressing from reconnaissance to live "
        "incident response across 10 hands-on exercises."
    ),
    "icon": "network",
    "color": "#0EA5E9",
    "sort_order": 19,
    "levels": [
        {"level_number": 1, "name": "Foundations",
         "description": "Map the Arcline network and lock down the perimeter with router ACLs"},
        {"level_number": 2, "name": "Detection",
         "description": "Baseline normal traffic and catch lateral movement with IDS sensors"},
        {"level_number": 3, "name": "Segmentation and Hardening",
         "description": "Carve flat networks into segments and spot firewall bypass attempts"},
        {"level_number": 4, "name": "Incident Response",
         "description": "Investigate a compromised router and trace a multi-segment kill chain"},
        {"level_number": 5, "name": "Architecture and Capstone",
         "description": "Review a network design and defend the network under live attack"},
    ],
}


def seed_netdef():
    db = SessionLocal()
    try:
        track = dict(TRACK)
        levels = track.pop("levels")
        slug = track["slug"]

        existing = db.execute(
            text("SELECT id FROM tracks WHERE slug = :slug"), {"slug": slug}
        ).fetchone()
        if existing:
            track_id = existing[0]
            db.execute(text("""
                UPDATE tracks SET name=:name, description=:description, icon=:icon,
                    color=:color, sort_order=:sort_order, is_active=TRUE
                WHERE slug=:slug
            """), track)
            print(f"updated track netdef (id={track_id})")
        else:
            track_id = db.execute(text("""
                INSERT INTO tracks (name, slug, description, icon, color, sort_order, is_active)
                VALUES (:name, :slug, :description, :icon, :color, :sort_order, TRUE)
                RETURNING id
            """), track).fetchone()[0]
            print(f"created track netdef (id={track_id})")

        for lv in levels:
            ex = db.execute(text(
                "SELECT id FROM levels WHERE track_id=:t AND level_number=:n"),
                {"t": track_id, "n": lv["level_number"]}).fetchone()
            params = {"track_id": track_id, "level_number": lv["level_number"],
                      "name": lv["name"], "description": lv["description"],
                      "sort_order": lv["level_number"]}
            if ex:
                db.execute(text("""
                    UPDATE levels SET name=:name, description=:description, sort_order=:sort_order
                    WHERE track_id=:track_id AND level_number=:level_number
                """), params)
                print(f"  updated level {lv['level_number']}: {lv['name']}")
            else:
                db.execute(text("""
                    INSERT INTO levels (track_id, level_number, name, description, sort_order)
                    VALUES (:track_id, :level_number, :name, :description, :sort_order)
                """), params)
                print(f"  created level {lv['level_number']}: {lv['name']}")

        db.commit()
        print("netdef track + 5 levels committed")
    finally:
        db.close()


if __name__ == "__main__":
    seed_netdef()
