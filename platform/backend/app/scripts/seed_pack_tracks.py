#!/usr/bin/env python3
"""Data-driven per-pack track/level seeder.

Seeds only the track slugs requested, from pack_seeds/pack_tracks.json (the
ground-truth track+level definitions). Each content pack seeds its own
track(s), so a fresh edition install populates exactly the packs it ships and
nothing else. Idempotent upsert, matching seed_curriculum's schema handling.

Usage:
    python -m app.scripts.seed_pack_tracks netsec coffeeshop
    python -m app.scripts.seed_pack_tracks --all
"""
import json
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://labuser:labpass@db:5432/labdb")
DATA = os.path.join(os.path.dirname(__file__), "pack_seeds", "pack_tracks.json")


def load_defs():
    with open(DATA) as f:
        return {t["slug"]: t for t in json.load(f)}


def seed(slugs):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    defs = load_defs()
    tc = lc = 0
    try:
        for slug in slugs:
            t = defs.get(slug)
            if not t:
                print(f"  WARN: no track def for '{slug}' in pack_tracks.json")
                continue
            row = db.execute(text("SELECT id FROM tracks WHERE slug=:s"), {"s": slug}).fetchone()
            params = {
                "name": t["name"], "slug": slug, "description": t.get("description", ""),
                "icon": t.get("icon"), "color": t.get("color"), "sort_order": t.get("sort_order", 0),
            }
            if row:
                track_id = row[0]
                db.execute(text(
                    "UPDATE tracks SET name=:name, description=:description, icon=:icon, "
                    "color=:color, sort_order=:sort_order, is_active=TRUE WHERE slug=:slug"), params)
            else:
                track_id = db.execute(text(
                    "INSERT INTO tracks (name, slug, description, icon, color, sort_order, is_active) "
                    "VALUES (:name,:slug,:description,:icon,:color,:sort_order,TRUE) RETURNING id"),
                    params).fetchone()[0]
                tc += 1
            for lv in (t.get("levels") or []):
                lp = {"tid": track_id, "ln": lv["level_number"], "name": lv["name"],
                      "desc": lv.get("description", ""), "so": lv["level_number"]}
                ex = db.execute(text(
                    "SELECT id FROM levels WHERE track_id=:tid AND level_number=:ln"), lp).fetchone()
                if ex:
                    db.execute(text(
                        "UPDATE levels SET name=:name, description=:desc, sort_order=:so "
                        "WHERE track_id=:tid AND level_number=:ln"), lp)
                else:
                    db.execute(text(
                        "INSERT INTO levels (track_id, level_number, name, description, sort_order) "
                        "VALUES (:tid,:ln,:name,:desc,:so)"), lp)
                    lc += 1
            print(f"  seeded track {slug} ({len(t.get('levels') or [])} levels)")
        db.commit()
        print(f"done: {tc} new tracks, {lc} new levels")
    finally:
        db.close()


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: seed_pack_tracks.py <slug> [<slug>...] | --all", file=sys.stderr)
        return 2
    if args == ["--all"]:
        args = list(load_defs().keys())
    seed(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
