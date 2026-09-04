#!/usr/bin/env python3
"""Wiki system generator.

Single source of truth is wikis.yaml at the repo root. This tool reads it (plus
the live course list) and emits every downstream artifact so the four registries
that used to drift by hand are now generated from one file:

  - nginx location blocks (range + course namespaces, auth tiers)
  - the frontend resolver map (slug -> serve_path + namespace + auth)
  - the build list (slug -> config, docs_dir, site_dir)
  - the /wiki/ index (range tracks only; courses never listed)
  - the wiki-doctor target list (every wiki + its expected auth tier)

Modes:
  summary           print the planned routing table (default)
  audit             current-vs-planned mismatch report (phase 1 deliverable)
  emit   --out DIR  write all generated artifacts into DIR
  check  --against DIR
                    emit to a temp dir and diff against a previously emitted DIR;
                    non-zero exit if they differ (the CI staleness gate)

Courses are dynamic: they are read from courses.json (exported from the DB) when
present, so adding a course needs no manifest edit. See PRD-Doc-Rebuild.md and
PHASE1-DISPOSITION.md.
"""

import argparse
import difflib
import json
import os
import sys
import tempfile

try:
    import yaml
except ImportError:
    sys.stderr.write("error: PyYAML required (pip install pyyaml, or run under the backend venv)\n")
    sys.exit(2)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MANIFEST = os.path.join(REPO_ROOT, "wikis.yaml")
COURSES_JSON = os.path.join(os.path.dirname(__file__), "courses.json")
# Generated registry consumed by the backend (build pipeline + course-slug
# collision guard). Committed into the backend package so it ships and syncs
# with the code; regenerated from wikis.yaml so it cannot drift.
BACKEND_REGISTRY = os.path.join(REPO_ROOT, "platform", "backend", "app", "wiki_registry.json")
# nginx configs whose generated block region is kept in sync (between sentinels).
NGINX_CONFS = [
    os.path.join(REPO_ROOT, "platform", "frontend", "nginx.conf"),
    os.path.join(REPO_ROOT, "platform", "frontend", "nginx-ssl.conf"),
]

# auth tier -> nginx auth_request subrequest (unchanged meaning)
AUTH_SUBREQUEST = {
    "student": "/_wiki_auth",
    "enrolled": "/_wiki_course_auth",
    "admin": "/_wiki_admin_auth",
}

# Served-content root inside the frontend container.
CONTENT_ROOT = "/usr/share/nginx/wiki"

# Audited current state (2026-06-13), used only by `audit` to diff old->new.
# slug -> (current_url_path, current_auth_subrequest)
CURRENT_STATE = {
    "winpt":       ("/wiki-courses/winpt/", "/_wiki_auth"),
    "linpt":       ("/wiki-courses/linpt/", "/_wiki_auth"),
    "netfor":      ("/wiki-courses/netfor/", "/_wiki_auth"),
    "webpt":       ("/wiki-courses/webpt/", "/_wiki_auth"),
}

NGINX_BEGIN = "    # === BEGIN generated wiki blocks (tools/wiki-gen) -- do not edit by hand ==="
NGINX_END = "    # === END generated wiki blocks ==="

# No 'unsafe-eval': mermaid, html2pdf, and the Material bundle run without eval.
# 'unsafe-inline' stays because MkDocs Material emits an inline bootstrap script on
# every generated page; a nonce/hash scheme would need the site builder to stamp each
# page, which the current pipeline does not do.
CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' "
    "https://unpkg.com https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'self'; base-uri 'self'; form-action 'self';"
)


def load_manifest():
    with open(MANIFEST) as f:
        return yaml.safe_load(f)


def load_courses():
    """Live course wikis: [{slug, theme, auth}]. Read from courses.json if present."""
    if os.path.exists(COURSES_JSON):
        with open(COURSES_JSON) as f:
            return json.load(f)
    return []


def serve_path(namespace, slug):
    return f"/wiki/{namespace}/{slug}/"


def content_path(namespace, slug):
    return f"{CONTENT_ROOT}/{namespace}/{slug}/"


def site_dir(slug):
    return f"_site_{slug}"


def wikis(manifest, courses):
    """Unified list of every wiki: (slug, namespace, auth, theme, config, docs_dir)."""
    out = []
    for slug, t in sorted(manifest.get("tracks", {}).items()):
        out.append({
            "slug": slug, "namespace": "range", "auth": t.get("auth", "student"),
            "theme": t.get("theme"), "config": t.get("config"),
            "docs_dir": t.get("docs_dir", "Workbook"),
        })
    for slug, r in sorted(manifest.get("reference", {}).items()):
        out.append({
            "slug": slug, "namespace": "reference", "auth": r.get("auth", "student"),
            "theme": r.get("theme"), "config": r.get("config"),
            "docs_dir": r.get("docs_dir", "Workbook"),
        })
    cdef = manifest.get("courses", {})
    cauth = cdef.get("default_auth", "enrolled")
    for c in sorted(courses, key=lambda c: c["slug"]):
        out.append({
            "slug": c["slug"], "namespace": "course", "auth": c.get("auth", cauth),
            "theme": c.get("theme"), "config": c.get("config"), "docs_dir": c.get("docs_dir", "Workbook"),
        })
    return out


# ── artifact builders ────────────────────────────────────────────────

# Slug shape a namespace block will serve. Deliberately strict: lowercase
# alphanumerics plus _ . - , no slashes and no leading dot, so the regex cannot
# be walked out of the namespace directory.
SLUG_RE = r"[a-z0-9][a-z0-9._-]*"


def build_nginx_namespace_block(namespace, auth, slugs):
    """One block per namespace, not per wiki.

    Serving is slug-agnostic on purpose: a content pack installed after the
    image was built drops its workbook into the mounted wiki tree and is served
    immediately, with no nginx regeneration and no frontend rebuild. Auth is a
    property of the namespace (range/reference are student, course is enrolled),
    so a namespace block can carry it without knowing the slug.

    `root` rather than `alias`, because the URL path already mirrors the on-disk
    layout (/wiki/<ns>/<slug>/... under /usr/share/nginx), so $uri maps straight
    through with no rewriting.
    """
    sub = AUTH_SUBREQUEST[auth]
    known = ", ".join(sorted(slugs)) if slugs else "(none baked)"
    return f"""    # {namespace}/* ({auth}) -- serves any slug in this namespace.
    # Baked at build time: {known}
    location ~ ^/wiki/{namespace}/{SLUG_RE}/ {{
        auth_request {sub};
        # Named locations, not "error_page 401 =302 /login". That form makes
        # nginx serve /login's CONTENT with a 302 status and no Location
        # header, so the browser is told to redirect with nowhere to go and
        # renders a blank page. A named location that returns 302 sends a real
        # Location.
        error_page 401 = @wiki_login;
        # 403 is authenticated but not entitled: not enrolled, or the chapter
        # belongs to a week that has not opened. The course list shows the
        # release dates, so it answers the question they arrive with.
        error_page 403 = @wiki_denied;

        root {os.path.dirname(CONTENT_ROOT)};
        index index.html;
        try_files $uri $uri/ $uri/index.html =404;

        # HTML stays uncached (a workbook edit shows immediately); static
        # assets (images/css/js) are cacheable so they are not re-downloaded on
        # every page view. Driven by the $wiki_cache_control map on $uri.
        add_header Cache-Control $wiki_cache_control always;

        add_header Content-Security-Policy "{CSP}" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
    }}
"""


def build_nginx_redirect_blocks():
    """Named locations the wiki auth failures redirect to.

    Kept separate from the per-namespace blocks so both 401 and 403 resolve to
    a real Location header rather than nginx serving another page's body under
    a redirect status.
    """
    return """    # Wiki auth outcomes -> real redirects (see error_page above).
    location @wiki_login {
        return 302 /login;
    }
    location @wiki_denied {
        return 302 /courses;
    }
"""


def build_nginx_index_block():
    """The /wiki/ landing: range-only index, student auth, no content fallback."""
    return f"""    # /wiki/ landing index (range tracks only; no chapter content here)
    location = /wiki/ {{
        auth_request /_wiki_auth;
        error_page 401 =302 /login;
        error_page 403 =302 /login;

        alias {CONTENT_ROOT}/;
        index index.html;
        try_files /index.html =404;

        add_header Cache-Control $wiki_cache_control always;
        add_header Content-Security-Policy "{CSP}" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
    }}
"""


def build_nginx(all_wikis):
    parts = [NGINX_BEGIN, ""]
    parts.append(build_nginx_redirect_blocks())
    parts.append(build_nginx_index_block())
    # Group by (namespace, auth). Auth is currently a function of namespace, so
    # this yields one block per namespace; the grouping is kept explicit so a
    # future namespace with a different auth tier fails loudly here rather than
    # silently serving under the wrong subrequest.
    groups = {}
    for w in all_wikis:
        groups.setdefault((w["namespace"], w["auth"]), []).append(w["slug"])
    by_ns = {}
    for (ns, auth) in groups:
        by_ns.setdefault(ns, set()).add(auth)
    for ns, auths in sorted(by_ns.items()):
        if len(auths) > 1:
            raise SystemExit(
                f"ERROR: namespace '{ns}' mixes auth tiers {sorted(auths)}. "
                "A namespace-wide nginx block cannot express per-slug auth; "
                "split the namespace or reintroduce per-slug blocks for it.")
    for (ns, auth), slugs in sorted(groups.items()):
        parts.append(build_nginx_namespace_block(ns, auth, slugs))
    parts.append(NGINX_END + "\n")
    return "\n".join(parts)


def build_resolver(all_wikis):
    """Frontend resolver map. Course-vs-range is decided by lab visibility at
    call time; this map is keyed by slug so a fully-qualified workbook field
    (wiki/range/<slug>/...) resolves directly."""
    return {
        w["slug"]: {"namespace": w["namespace"], "serve_path": serve_path(w["namespace"], w["slug"]),
                    "auth": w["auth"]}
        for w in all_wikis
    }


def build_list(all_wikis):
    return {
        w["slug"]: {"config": w["config"], "docs_dir": w["docs_dir"],
                    "site_dir": site_dir(w["slug"]), "namespace": w["namespace"]}
        for w in all_wikis if w["config"]
    }


def build_doctor_targets(all_wikis):
    return [
        {"slug": w["slug"], "namespace": w["namespace"],
         "serve_path": serve_path(w["namespace"], w["slug"]), "expected_auth": w["auth"]}
        for w in all_wikis
    ]


def build_index_md(all_wikis):
    lines = ["# OpenCyberRange Wikis", "",
             "General range tracks. Course material is not listed here.", ""]
    for w in all_wikis:
        if w["namespace"] != "range":
            continue
        if w["auth"] == "admin":
            continue  # staff-only reference tracks are not listed in the general index
        lines.append(f"- [{w['slug']}]({serve_path('range', w['slug'])})")
    ref = [w for w in all_wikis if w["namespace"] == "reference"]
    if ref:
        lines += ["", "## Reference", ""]
        for w in ref:
            lines.append(f"- [{w['slug']}]({serve_path('reference', w['slug'])})")
    return "\n".join(lines) + "\n"


# ── modes ────────────────────────────────────────────────────────────

def build_index_html(all_wikis):
    items = "\n".join(
        f'    <li><a href="{serve_path("range", w["slug"])}">{w["slug"]}</a></li>'
        for w in all_wikis if w["namespace"] == "range" and w["auth"] != "admin"
    )
    ref = [w for w in all_wikis if w["namespace"] == "reference"]
    ref_section = ""
    if ref:
        ref_items = "\n".join(
            f'    <li><a href="{serve_path("reference", w["slug"])}">{w["slug"]}</a></li>'
            for w in ref
        )
        ref_section = f"<h2>Reference</h2>\n<ul>\n{ref_items}\n</ul>\n"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenCyberRange Wikis</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:680px;margin:3rem auto;padding:0 1rem;color:#1a1a1a}}
 h1{{font-size:1.6rem}} h2{{font-size:1.2rem;margin-top:2rem}} p{{color:#555}}
 ul{{list-style:none;padding:0}} li{{margin:.4rem 0}}
 a{{display:inline-block;padding:.5rem .8rem;background:#f3f4f6;border-radius:6px;text-decoration:none;color:#1f2937}}
 a:hover{{background:#e5e7eb}}
</style></head><body>
<h1>OpenCyberRange Wikis</h1>
<p>General range tracks. Course material is not listed here.</p>
<ul>
{items}
</ul>
{ref_section}</body></html>
"""


def _splice_nginx(blocks):
    """Replace the generated region (between the BEGIN/END sentinels) in each
    nginx conf with the freshly generated blocks. Skips a conf that has no
    sentinels (so it never corrupts a hand-managed file)."""
    begin = NGINX_BEGIN.strip()
    end = NGINX_END.strip()
    spliced = []
    for path in NGINX_CONFS:
        if not os.path.exists(path):
            continue
        lines = open(path).read().splitlines(keepends=True)
        try:
            b = next(i for i, l in enumerate(lines) if begin in l)
            e = next(i for i, l in enumerate(lines) if end in l)
        except StopIteration:
            continue
        with open(path, "w") as f:
            f.write("".join(lines[:b]) + blocks + "".join(lines[e + 1:]))
        spliced.append(os.path.basename(path))
    return spliced


def emit(out_dir, all_wikis):
    os.makedirs(out_dir, exist_ok=True)
    artifacts = {
        "nginx_wiki_blocks.conf": build_nginx(all_wikis),
        "resolver.json": json.dumps(build_resolver(all_wikis), indent=2, sort_keys=True) + "\n",
        "build_list.json": json.dumps(build_list(all_wikis), indent=2, sort_keys=True) + "\n",
        "wiki_doctor_targets.json": json.dumps(build_doctor_targets(all_wikis), indent=2) + "\n",
        "index.md": build_index_md(all_wikis),
        "index.html": build_index_html(all_wikis),
    }
    for name, content in artifacts.items():
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(content)
    # Backend registry: tracks only (slug -> config, docs_dir, theme, auth).
    # Written both to out_dir (for --check) and into the backend package.
    manifest = load_manifest()
    registry = json.dumps({"tracks": manifest.get("tracks", {})},
                          indent=2, sort_keys=True) + "\n"
    with open(os.path.join(out_dir, "wiki_registry.json"), "w") as f:
        f.write(registry)
    if os.path.isdir(os.path.dirname(BACKEND_REGISTRY)):
        with open(BACKEND_REGISTRY, "w") as f:
            f.write(registry)
    # Splice the generated nginx blocks into the real configs.
    spliced = _splice_nginx(artifacts["nginx_wiki_blocks.conf"])
    return list(artifacts) + ["wiki_registry.json"] + [f"nginx:{s}" for s in spliced]


def cmd_summary(all_wikis):
    print(f"{'slug':<14} {'namespace':<8} {'auth':<9} {'serve_path':<26} config")
    print("-" * 88)
    for w in all_wikis:
        print(f"{w['slug']:<14} {w['namespace']:<8} {w['auth']:<9} "
              f"{serve_path(w['namespace'], w['slug']):<26} {w['config'] or '(dynamic)'}")
    print(f"\n{len(all_wikis)} wikis "
          f"({sum(1 for w in all_wikis if w['namespace']=='range')} range, "
          f"{sum(1 for w in all_wikis if w['namespace']=='reference')} reference, "
          f"{sum(1 for w in all_wikis if w['namespace']=='course')} course)")


def cmd_audit(all_wikis):
    by_slug = {w["slug"]: w for w in all_wikis}
    print("Current vs planned (mismatches the rebuild resolves)\n")
    print(f"{'slug':<13} {'current path':<26} {'cur auth':<10} {'planned path':<22} {'new auth':<10} change")
    print("-" * 104)
    changes = 0
    for slug, (cur_path, cur_sub) in sorted(CURRENT_STATE.items()):
        w = by_slug.get(slug)
        if not w:
            print(f"{slug:<13} {cur_path:<26} {cur_sub.replace('/_wiki_',''):<10} {'(removed)':<22}")
            changes += 1
            continue
        new_path = serve_path(w["namespace"], w["slug"])
        new_sub = AUTH_SUBREQUEST[w["auth"]]
        flags = []
        if cur_path != new_path:
            flags.append("PATH")
        if cur_sub != new_sub:
            flags.append(f"AUTH {cur_sub.replace('/_wiki_','')}->{new_sub.replace('/_wiki_','')}")
        if flags:
            changes += 1
        print(f"{slug:<13} {cur_path:<26} {cur_sub.replace('/_wiki_',''):<10} "
              f"{new_path:<22} {new_sub.replace('/_wiki_',''):<10} {', '.join(flags)}")
    extra = [w for w in all_wikis if w["slug"] not in CURRENT_STATE]
    if extra:
        print("\nNew wikis not in current nginx (courses + dynamic):")
        for w in extra:
            print(f"  {w['slug']:<13} {w['namespace']}  {serve_path(w['namespace'], w['slug'])}")
    print(f"\n{changes} tracks change path and/or auth tier.")


def cmd_check(against_dir, all_wikis):
    tmp = tempfile.mkdtemp(prefix="wiki-gen-")
    names = emit(tmp, all_wikis)
    differs = False
    for name in names:
        if name.startswith("nginx:"):
            continue  # nginx splices are in-place edits, not files in the emit dir
        new = open(os.path.join(tmp, name)).read()
        old_path = os.path.join(against_dir, name)
        old = open(old_path).read() if os.path.exists(old_path) else ""
        if new != old:
            differs = True
            print(f"DRIFT: {name}")
            for line in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                             fromfile=f"committed/{name}", tofile=f"generated/{name}", lineterm=""):
                print(line)
    if differs:
        print("\ncheck FAILED: committed artifacts are stale; re-run emit and commit.")
        return 1
    print("check OK: committed artifacts match the manifest.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="OpenCyberRange wiki generator")
    ap.add_argument("mode", nargs="?", default="summary",
                    choices=["summary", "audit", "emit", "check"])
    ap.add_argument("--out", help="output dir for emit")
    ap.add_argument("--against", help="committed artifact dir for check")
    args = ap.parse_args()

    manifest = load_manifest()
    courses = load_courses()
    all_wikis = wikis(manifest, courses)

    if args.mode == "summary":
        cmd_summary(all_wikis)
    elif args.mode == "audit":
        cmd_audit(all_wikis)
    elif args.mode == "emit":
        if not args.out:
            ap.error("emit requires --out DIR")
        written = emit(args.out, all_wikis)
        print(f"wrote {len(written)} artifacts to {args.out}: {', '.join(written)}")
    elif args.mode == "check":
        if not args.against:
            ap.error("check requires --against DIR")
        sys.exit(cmd_check(args.against, all_wikis))


if __name__ == "__main__":
    main()
