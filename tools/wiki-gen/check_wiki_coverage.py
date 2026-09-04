#!/usr/bin/env python3
"""wiki-coverage: catch a course whose workbook was never built into the image.

The failure this exists to prevent: a course can carry a wiki_slug, be listed
in the generator's courses.json, and have its source workbook in the repo, and
still 404 for every enrolled student, because the built output never reached
the frontend build context. The image then ships with fewer course wikis than
the database expects and nothing anywhere reports it.

Why this runs at deploy time rather than as a backend startup check. On a baked
image there is no shared wiki volume, so the backend cannot stat the files at
all. It could probe nginx over HTTP, but the course wiki location runs
auth_request first and returns 302 to an unauthenticated caller, so a probe
without a student's cookie can never tell a missing wiki from a gated one. The
only place all three facts are visible at once is here, before the build.

Three sources have to agree:

  database          courses.wiki_slug     what a student will actually request
  courses.json      the generator's list  what the build knows how to produce
  build context     wiki/course/<slug>/   what will be baked into the image

A slug in the database with no build context directory is a broken workbook.
That is the only condition that fails the check; the rest is reported so the
drift is visible before it becomes an outage.

Usage:
  # dev, comparing generator config against the local build context
  python3 check_wiki_coverage.py

  # include the live course list from a running database
  python3 check_wiki_coverage.py --psql 'docker exec ocr-db psql -U labuser -d labdb'

  # a remote range: build context and database both live there
  python3 check_wiki_coverage.py --remote RANGEHOST --build-context ~/ocr/frontend \\
      --psql 'ssh RANGEHOST docker exec ocr-db psql -U labuser -d labdb'

Exit status is 1 when a database slug has no built output, so this can gate a
deploy script. Everything else exits 0.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

SLUG_QUERY = (
    "SELECT wiki_slug FROM courses "
    "WHERE wiki_slug IS NOT NULL AND btrim(wiki_slug) <> ''"
)


def db_slugs(psql_cmd):
    """Course slugs the database expects, or None when no --psql was given.

    Returns None rather than an empty set on failure, so "could not ask" is
    never mistaken for "the database wants nothing".
    """
    if not psql_cmd:
        return None
    # Build argv rather than a shell string. Over ssh the command crosses two
    # shells, and the SQL carries spaces, quotes and parentheses that the remote
    # one will happily mangle, so quote the statement for that second shell and
    # leave it bare when running locally.
    argv = shlex.split(psql_cmd) + ["-tAc"]
    argv.append(shlex.quote(SLUG_QUERY) if argv[0] == "ssh" else SLUG_QUERY)
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except (subprocess.SubprocessError, OSError) as exc:
        print("  ! could not query the database: %s" % exc)
        return None
    if out.returncode != 0:
        print("  ! database query failed: %s" % (out.stderr or "").strip()[:200])
        return None
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def generator_slugs(courses_json):
    if not os.path.isfile(courses_json):
        print("  ! no courses.json at %s" % courses_json)
        return set(), {}
    with open(courses_json) as fh:
        entries = json.load(fh)
    return ({e["slug"] for e in entries if e.get("slug")},
            {e["slug"]: e.get("config", "") for e in entries if e.get("slug")})


def built_slugs(build_context, remote):
    """Slugs with a built wiki in the frontend build context.

    `remote` is an ssh destination when the build context lives on another
    machine. It is deliberately separate from --psql: checking a local build
    against a live remote database is a normal thing to want, and inferring the
    location of one from the other listed the wrong machine's files.
    """
    course_dir = os.path.join(build_context, "wiki", "course")
    if remote:
        script = ('for d in %s/*/; do [ -f "$d/index.html" ] && basename "$d"; done'
                  % course_dir)
        out = subprocess.run(["ssh", remote, script],
                             capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            print("  ! could not list %s on %s" % (course_dir, remote))
        return {l.strip() for l in out.stdout.splitlines() if l.strip()}

    if not os.path.isdir(course_dir):
        print("  ! no build context wiki dir at %s" % course_dir)
        return set()
    found = set()
    for name in sorted(os.listdir(course_dir)):
        # index.html is the test, not the directory: an empty or half-synced
        # directory serves 404s exactly like a missing one.
        if os.path.isfile(os.path.join(course_dir, name, "index.html")):
            found.add(name)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-context", default=os.path.join(REPO, "platform", "frontend"),
                    help="frontend build context holding wiki/course/ (default: the repo's)")
    ap.add_argument("--courses-json", default=os.path.join(HERE, "courses.json"))
    ap.add_argument("--remote", default="",
                    help="ssh destination when the build context is on another machine")
    ap.add_argument("--psql", default="",
                    help="command that runs psql against the platform database")
    args = ap.parse_args()

    print("wiki coverage")
    print("  build context : %s%s" % (
        (args.remote + ":") if args.remote else "", args.build_context))

    gen, configs = generator_slugs(args.courses_json)
    built = built_slugs(args.build_context, args.remote)
    db = db_slugs(args.psql)

    every = sorted(gen | built | (db or set()))
    if not every:
        print("  nothing to check")
        return 0

    print()
    print("  %-16s %-4s %-4s %-6s %s" % ("slug", "db", "gen", "built", "config"))
    print("  " + "-" * 62)
    broken = []
    for slug in every:
        in_db = "-" if db is None else ("yes" if slug in db else "no")
        row = (slug,
               in_db,
               "yes" if slug in gen else "no",
               "yes" if slug in built else "NO",
               configs.get(slug, ""))
        print("  %-16s %-4s %-4s %-6s %s" % row)
        if db is not None and slug in db and slug not in built:
            broken.append(slug)

    print()
    if db is None:
        print("  database not consulted; pass --psql to check what students will request")

    if broken:
        print("  BROKEN: %d course wiki(s) the database expects have no built output." % len(broken))
        for slug in broken:
            print("     /wiki/course/%s/ will 404 for every enrolled student" % slug)
        print("  Build it and sync it into the build context before building the frontend image.")
        return 1

    stale = sorted(built - gen)
    if stale:
        print("  note: built but not in courses.json: %s" % ", ".join(stale))
    unbuilt = sorted(gen - built)
    if unbuilt:
        print("  note: in courses.json but not built: %s" % ", ".join(unbuilt))
    if db is None:
        print("  INCOMPLETE: config and build context compared, database not checked.")
        return 0
    print("  OK: every course wiki the database expects is present in the build context.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
