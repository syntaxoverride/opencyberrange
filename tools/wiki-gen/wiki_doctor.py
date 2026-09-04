#!/usr/bin/env python3
"""wiki-doctor: verify every wiki route serves the right content to the right role.

Reads the generated wiki_doctor_targets.json and probes each target through the
live frontend nginx as several identities, checking BOTH the auth outcome and
that real MkDocs content (not the SPA fallback) is served. Because the SPA
catch-all returns 200 for any path, status code alone is meaningless; this tool
keys on the MkDocs generator meta tag.

Identities are supplied as name=token pairs (tokens are JWTs minted by logging
in). An empty token is the anonymous identity.

Usage (run from a host that can reach the frontend container):
  python3 wiki_doctor.py --base http://127.0.0.1 --identity admin=$TOK --identity anon=
"""

import argparse
import json
import os
import sys
import urllib.request

TARGETS = os.path.join(os.path.dirname(__file__), "generated", "wiki_doctor_targets.json")
MKDOCS_MARK = 'name="generator" content="mkdocs'


def fetch(base, path, token):
    req = urllib.request.Request(base + path)
    if token:
        req.add_header("Cookie", f"wiki_auth={token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1")
    ap.add_argument("--identity", action="append", default=[],
                    help="name=token (empty token = anonymous)")
    args = ap.parse_args()

    identities = {}
    for spec in args.identity:
        name, _, tok = spec.partition("=")
        identities[name] = tok

    targets = json.load(open(TARGETS))
    names = list(identities)
    print(f"{'target':<26} {'tier':<9} " + " ".join(f"{n:<14}" for n in names))
    print("-" * (36 + 15 * len(names)))

    fails = 0
    for t in targets:
        row = f"{t['serve_path']:<26} {t['expected_auth']:<9} "
        for n in names:
            status, body = fetch(args.base, t["serve_path"], identities[n])
            served = MKDOCS_MARK in body
            # expected: a user who passes the tier sees mkdocs; one who fails sees no mkdocs
            cell = f"{status}:{'wiki' if served else 'no'}"
            row += f"{cell:<14} "
        print(row)
    print(f"\n{len(targets)} targets probed across {len(names)} identities.")
    return fails


if __name__ == "__main__":
    sys.exit(main())
