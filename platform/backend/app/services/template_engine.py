"""Exercise Studio template engine (Phase 0).

Loads vetted lab templates from ``platform/templates/`` and instantiates them:
deep-merges an instructor's cosmetic overrides onto the template's de-identified
defaults, validates the result against the template's ``cosmetic_schema``,
renders a draft lab directory under ``platform/labs/<Track>/``, and ingests it
via the existing ``discover_labs`` path as ``visibility: draft``.

Phase 0 scope (see PRD-Exercise-Studio.md section 11):
  * Only the cosmetic (skinnable) zone is editable; the structural zone is
    locked. A template never carries an absolute IP -- the orchestrator owns
    networking via ``ip_offset`` labels -- so re-subnetting per instance is
    automatic and nothing here touches it.
  * Per-instance ``FLAG`` / ``CRED_<role>_*`` values are NOT baked into the
    rendered images. They are written into the rendered ``lab.yaml`` (so the
    flag hash and tester resolve) and injected at spawn by
    ``docker_manager._inject_template_instance_env`` (Build Step 3). The
    container entrypoints read them from the environment with a baked fallback,
    so the image still runs standalone.

Nothing in this module mutates the template sources; rendering only ever writes
under the draft lab directory it creates.
"""

import json
import os
import re
import secrets
import shutil

import yaml

# ---------------------------------------------------------------------------
# Path resolution
#
# Inside the backend container the labs tree is mounted at ``/labs`` and the app
# at ``/app`` (so templates live at ``/app/templates`` only if baked in). In the
# dev repo both live under ``platform/``. Resolve from this file's location with
# environment overrides so the engine works in both layouts without a rewrite.
# ---------------------------------------------------------------------------

# .../platform/backend/app/services/template_engine.py -> .../platform
_PLATFORM_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
)


def _first_existing(*candidates):
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    # Fall back to the first candidate even if it does not yet exist so callers
    # get a deterministic, debuggable path rather than None.
    return candidates[0]


TEMPLATES_DIR = os.environ.get("STUDIO_TEMPLATES_DIR") or _first_existing(
    "/app/templates",
    os.path.join(_PLATFORM_DIR, "templates"),
)

# The labs root the running container ingests from is ``/labs``; in the dev repo
# it is ``platform/labs``. discover_labs reads from LABS_DIR (default /labs).
LABS_DIR = os.environ.get("LABS_DIR") or _first_existing(
    "/labs",
    os.path.join(_PLATFORM_DIR, "labs"),
)

# Map an archetype to the labs/ track subdirectory discover_labs walks.
# discover_labs keys tracks by the lowercased dir name's parsed slug, so the
# directory casing here only has to be a directory it will scan.
_TRACK_SUBDIR = {
    "linux": "Linux",
    "network": "Network",
    "web": "Web",
    "windows": "Windows",
}


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

class TemplateError(Exception):
    """Raised on a malformed template or an invalid instantiation request."""


# A template slug is a single, lowercase, filesystem-safe directory name. It is
# never a path: no separators, no parent refs, no leading dot. Validating here
# (and asserting the resolved path stays inside TEMPLATES_DIR / LABS_DIR below)
# closes the path-traversal primitive an instructor could otherwise use to copy
# arbitrary on-disk trees into the labs tree or read template.yaml files outside
# the catalog.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")


def _validate_slug(slug):
    """Reject anything that is not a plain catalog slug. Returns the slug.

    Defends every filesystem use of the slug (template read, copytree source,
    rendered dest). ``..``, ``/``, leading dots and the empty string all fail
    the regex, so a caller can never escape TEMPLATES_DIR through the slug.
    """
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise TemplateError(f"invalid template slug: {slug!r}")
    return slug


def _assert_within(path, root, label):
    """Assert ``path`` resolves inside ``root`` (defence in depth past the regex)."""
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(root)
    if real_path != real_root and not real_path.startswith(real_root + os.sep):
        raise TemplateError(f"{label} escapes its root: {path!r}")
    return real_path


def _load_template_yaml(slug):
    """Load and parse a template.yaml for ``slug``. Returns the raw dict."""
    _validate_slug(slug)
    path = os.path.join(TEMPLATES_DIR, slug, "template.yaml")
    _assert_within(path, TEMPLATES_DIR, "template path")
    if not os.path.isfile(path):
        raise TemplateError(f"template not found: {slug}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise TemplateError(f"template.yaml for {slug} is not a mapping")
    return data


def _cosmetic_defaults(manifest):
    """Pull the default value out of every cosmetic_schema property.

    For ``object``-typed properties (for example ``flag``: {mode, value}) the
    defaults live in the nested ``properties`` rather than a top-level
    ``default``, so synthesize the object from its children. Without this the
    field would be absent from the defaults dict and an instructor's override
    for it would be silently dropped by ``_merge_overrides``.
    """
    schema = manifest.get("cosmetic_schema", {}) or {}
    props = schema.get("properties", {}) or {}
    out = {}
    for name, spec in props.items():
        if not isinstance(spec, dict):
            continue
        if "default" in spec:
            out[name] = spec["default"]
        elif spec.get("type") == "object":
            nested = {}
            for fname, fspec in (spec.get("properties", {}) or {}).items():
                if isinstance(fspec, dict) and "default" in fspec:
                    nested[fname] = fspec["default"]
            if nested:
                out[name] = nested
    return out


def _topology_nodes(manifest):
    """Return the structural topology nodes as a list of dicts."""
    return (manifest.get("structural", {}) or {}).get("topology", {}).get("nodes", []) or []


def _to_summary(slug, manifest):
    """Shape a template into the dict the frontend (studioMock.js) expects.

    Matches the studioMock.js template object: id/slug/name/klass/archetype/
    difficulty/description/tags/version/nodes/cosmetic. ``id`` is the slug here;
    the router layers the DB row id on top when one exists.
    """
    structural = manifest.get("structural", {}) or {}
    cosmetic = _cosmetic_defaults(manifest)
    nodes = [
        {"label": n.get("label") or n.get("id"), "offset": _coerce_offset(n.get("ip_offset"))}
        for n in _topology_nodes(manifest)
    ]
    return {
        "id": slug,
        "slug": manifest.get("template_id", slug),
        "name": manifest.get("name", slug),
        "klass": manifest.get("class", "ephemeral"),
        "archetype": manifest.get("archetype", "linux"),
        "difficulty": structural.get("difficulty", "beginner"),
        "description": (manifest.get("description") or "").strip(),
        "tags": manifest.get("tags", []) or [],
        "version": int(manifest.get("version", 1) or 1),
        "sourceLabSlug": manifest.get("source_lab_slug"),
        "nodes": nodes,
        "cosmetic": cosmetic,
    }


def _coerce_offset(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return val


def list_templates():
    """Return a list of template summaries discovered under TEMPLATES_DIR."""
    out = []
    if not os.path.isdir(TEMPLATES_DIR):
        return out
    for slug in sorted(os.listdir(TEMPLATES_DIR)):
        tdir = os.path.join(TEMPLATES_DIR, slug)
        if not os.path.isdir(tdir):
            continue
        if not os.path.isfile(os.path.join(tdir, "template.yaml")):
            continue
        try:
            manifest = _load_template_yaml(slug)
        except TemplateError:
            continue
        out.append(_to_summary(slug, manifest))
    return out


def get_template(slug):
    """Return the full manifest dict plus a summary for a single template."""
    manifest = _load_template_yaml(slug)
    summary = _to_summary(slug, manifest)
    summary["manifest"] = {
        "structural": manifest.get("structural", {}),
        "cosmetic_schema": manifest.get("cosmetic_schema", {}),
        "env_contract": manifest.get("env_contract", {}),
    }
    return summary


# ---------------------------------------------------------------------------
# Override validation (cosmetic zone only)
# ---------------------------------------------------------------------------

def _merge_overrides(defaults, overrides):
    """Shallow-merge instructor overrides onto cosmetic defaults.

    Only keys declared in the cosmetic schema (i.e. present in ``defaults``) are
    accepted; anything else is ignored so an instructor can never reach into the
    structural zone through the override blob.
    """
    merged = json.loads(json.dumps(defaults))  # deep copy via json round-trip
    if not overrides:
        return merged
    for key, value in overrides.items():
        if key in merged:
            merged[key] = value
    return merged


def _validate_cosmetic(manifest, values):
    """Validate merged cosmetic values against the schema. Returns error list.

    Enforces the platform standards the linters also catch, but earlier and with
    a structured message: required fields, length bounds, regex patterns, enum
    membership, no ``!`` in passwords, OCR flag format. An empty list means OK.
    """
    errors = []
    schema = manifest.get("cosmetic_schema", {}) or {}
    props = schema.get("properties", {}) or {}

    for req in schema.get("required", []) or []:
        if not values.get(req):
            errors.append(f"required cosmetic field missing: {req}")

    for name, spec in props.items():
        if name not in values:
            continue
        val = values[name]
        ftype = spec.get("type")

        if ftype == "string" or ftype == "textarea":
            if not isinstance(val, str):
                errors.append(f"{name}: expected string")
                continue
            _check_str(name, val, spec, errors)
        elif ftype == "enum":
            allowed = spec.get("values", [])
            if val not in allowed:
                errors.append(f"{name}: '{val}' not in {allowed}")
        elif ftype == "array":
            if not isinstance(val, list):
                errors.append(f"{name}: expected list")
            elif spec.get("maxItems") and len(val) > spec["maxItems"]:
                errors.append(f"{name}: too many items (max {spec['maxItems']})")
            else:
                _check_array_items(name, val, spec, errors)
        elif ftype == "object":
            _check_object(name, val, spec, errors)

    # Credentials and flag get a hard pass for the platform's two non-negotiable
    # rules regardless of where they sit in the schema.
    for cred in values.get("credentials", []) or []:
        pw = (cred.get("pass") if isinstance(cred, dict) else "") or ""
        if "!" in pw:
            errors.append(f"credential '{cred.get('role', '?')}': password contains '!' (use '#')")
    flag = values.get("flag")
    if isinstance(flag, dict):
        fv = flag.get("value", "")
        if fv and not re.match(r"^OCR\{[a-z0-9_]+\}$", fv):
            errors.append(f"flag value '{fv}' must match OCR{{[a-z0-9_]+}}")

    return errors


def _check_str(name, val, spec, errors):
    if spec.get("minLength") and len(val) < spec["minLength"]:
        errors.append(f"{name}: too short (min {spec['minLength']})")
    if spec.get("maxLength") and len(val) > spec["maxLength"]:
        errors.append(f"{name}: too long (max {spec['maxLength']})")
    pat = spec.get("pattern")
    if pat and not re.match(pat, val):
        errors.append(f"{name}: '{val}' does not match pattern {pat}")


def _check_array_items(name, val, spec, errors):
    item_spec = spec.get("items")
    if not isinstance(item_spec, dict):
        return
    for idx, item in enumerate(val):
        if not isinstance(item, dict):
            continue
        for field, fspec in item_spec.items():
            if not isinstance(fspec, dict) or field not in item:
                continue
            fval = item[field]
            if fspec.get("enum") and fval not in fspec["enum"]:
                errors.append(f"{name}[{idx}].{field}: '{fval}' not in {fspec['enum']}")
            if isinstance(fval, str):
                _check_str(f"{name}[{idx}].{field}", fval, fspec, errors)


def _check_object(name, val, spec, errors):
    if not isinstance(val, dict):
        errors.append(f"{name}: expected object")
        return
    for field, fspec in (spec.get("properties", {}) or {}).items():
        if field not in val or not isinstance(fspec, dict):
            continue
        fval = val[field]
        if fspec.get("type") == "enum" and fval not in fspec.get("values", []):
            errors.append(f"{name}.{field}: '{fval}' not in {fspec.get('values')}")
        if isinstance(fval, str):
            _check_str(f"{name}.{field}", fval, fspec, errors)


# ---------------------------------------------------------------------------
# Flag and credential resolution
# ---------------------------------------------------------------------------

def _resolve_flag(manifest, values):
    """Return the concrete flag string for this instance.

    fixed mode  -> the configured value (or the structural fallback)
    auto mode   -> a fresh random flag, so per-instance rotation kills sharing
    """
    structural = manifest.get("structural", {}) or {}
    fallback = structural.get("flag_fallback", "OCR{flag}")
    flag = values.get("flag")
    if not isinstance(flag, dict):
        return fallback
    if flag.get("mode") == "auto":
        token = secrets.token_hex(6)
        return f"OCR{{{token}}}"
    return flag.get("value") or fallback


def _credentials_list(manifest, values):
    """Build the lab.yaml ``credentials:`` list from cosmetic overrides.

    Locks each role to the structural ``credential_roles`` definition while
    taking the username/password from the cosmetic override (or the fallback).
    """
    structural = manifest.get("structural", {}) or {}
    roles = structural.get("credential_roles", []) or []
    by_role = {}
    for c in values.get("credentials", []) or []:
        if isinstance(c, dict) and c.get("role"):
            by_role[c["role"]] = c
    out = []
    for rolespec in roles:
        role = rolespec.get("role")
        override = by_role.get(role, {})
        out.append({
            "username": override.get("user") or rolespec.get("user_fallback", ""),
            "password": override.get("pass") or rolespec.get("pass_fallback", ""),
            "role": role,
            "description": rolespec.get("description", ""),
        })
    return out


def _env_overrides(manifest, values, flag_value, credentials):
    """Per-SERVICE env var map the orchestrator injects at spawn.

    Returns ``{service_name: {VAR: VALUE}}`` so each FLAG / CRED_<role>_* value
    lands ONLY on the compose service the template's ``env_contract`` maps it to
    (via each variable's ``service`` field), never broadcast into peer
    containers. A variable with no declared ``service`` is dropped (the
    container's baked fallback applies) rather than leaked everywhere. This is
    what Build Step 3's docker_manager injection consumes; storing it on the
    instance keeps spawn-time injection a pure per-service lookup.
    """
    flat = {"FLAG": flag_value}
    for cred in credentials:
        role = cred.get("role")
        if not role:
            continue
        flat[f"CRED_{role}_USER"] = cred.get("username", "")
        flat[f"CRED_{role}_PASS"] = cred.get("password", "")

    contract = (manifest.get("env_contract", {}) or {}).get("variables", []) or []
    per_service = {}
    for var in contract:
        name = var.get("name")
        if name not in flat:
            continue
        targets = var.get("service")
        if isinstance(targets, str):
            targets = [targets]
        elif not isinstance(targets, list):
            targets = []
        for svc in targets:
            if isinstance(svc, str) and svc:
                per_service.setdefault(svc, {})[name] = flat[name]
    return per_service


# ---------------------------------------------------------------------------
# lab.yaml rendering
# ---------------------------------------------------------------------------

def _render_test_steps(manifest, flag_value):
    """Materialize the structural tester spec, substituting the flag literal.

    The structural ``test.steps`` use the platform tester grammar
    ({target.NODE}, {cred.ROLE.user/pass}, {flag}); only ``{flag}`` is resolved
    here so the stored flag_hash and the rendered expect line agree. The
    target/cred placeholders are resolved by the tester at run time exactly as
    for a hand-authored lab.
    """
    structural = manifest.get("structural", {}) or {}
    steps = json.loads(json.dumps(structural.get("test", {}).get("steps", []) or []))
    for step in steps:
        if isinstance(step.get("expect"), str):
            step["expect"] = step["expect"].replace("{flag}", flag_value)
    return {"steps": steps}


def _hostnames_for(manifest, values):
    """Resolve a per-node hostname list from the cosmetic hostname override."""
    nodes = _topology_nodes(manifest)
    host = values.get("hostname")
    if isinstance(host, list):
        return list(host)
    if isinstance(host, str) and host:
        # Single-node templates carry one string; multi-node carry a list. A
        # lone string applies to the first node only.
        return [host]
    return [n.get("label") or n.get("id") for n in nodes]


def render_lab_yaml(manifest, values, flag_value, credentials):
    """Build the lab.yaml dict for a rendered instance (cosmetic skin applied)."""
    structural = manifest.get("structural", {}) or {}
    topology = structural.get("topology", {}) or {}

    lab = {
        "name": manifest.get("name", manifest.get("template_id", "Lab")),
        "description": (values.get("scenario") or manifest.get("description") or "").strip()[:300],
        "difficulty": values.get("difficulty") or structural.get("difficulty", "beginner"),
        "category": structural.get("category", "general"),
        "duration_minutes": structural.get("duration_minutes", 60),
        "objectives": values.get("objectives") or [],
        "scenario": values.get("scenario", "").strip(),
        "flag": flag_value,
        "credentials": credentials,
        "topology": topology,
        "hostnames": _hostnames_for(manifest, values),
        "visibility": "draft",
        "test": _render_test_steps(manifest, flag_value),
    }
    # Drop empty optional keys so the rendered file stays clean.
    if not lab["objectives"]:
        del lab["objectives"]
    return lab


# ---------------------------------------------------------------------------
# Directory materialization
# ---------------------------------------------------------------------------

def _slugify_company(company):
    s = re.sub(r"[^a-z0-9]+", "-", (company or "").lower()).strip("-")
    return s or "instance"


def _rendered_dir_name(manifest, values, suffix):
    """Compute the lab directory name discover_labs will parse.

    discover_labs derives (track, level, lab_num) from the dir name, so the name
    must follow ``{track}-{level}-{lab_num}-{base_slug}``. To keep multiple
    instances of one template distinct we append a short company/random suffix
    to the base_slug (still parses: extra trailing segments stay in the slug).
    """
    structural = manifest.get("structural", {}) or {}
    track = structural.get("track", manifest.get("archetype", "linux"))
    level = structural.get("level", 1)
    lab_num = structural.get("lab_num", 1)
    base = structural.get("base_slug", manifest.get("template_id", "lab"))
    return f"{track}-{level}-{lab_num}-{base}-{suffix}"


def _apply_skin_to_text(text, replacements):
    """Apply display-only string replacements to a rendered support file.

    Only hostnames and a handful of brand strings get swapped; the exploit path,
    flag location and tester logic are never touched (those resolve from env at
    spawn). Replacements are applied longest-key-first to avoid partial hits.
    """
    for old, new in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        if old and new and old != new:
            text = text.replace(old, new)
    return text


def materialize_instance(slug, overrides, instance_key=None):
    """Render a template + cosmetic overrides into a draft lab directory.

    Returns a dict describing the materialized instance: the rendered lab dir,
    the parsed slug, the resolved flag, the per-instance env override map and the
    lab.yaml content. Does NOT ingest; the caller runs the publish gate first.

    Raises TemplateError with a joined message if validation fails.
    """
    manifest = _load_template_yaml(slug)
    defaults = _cosmetic_defaults(manifest)
    values = _merge_overrides(defaults, overrides)

    errors = _validate_cosmetic(manifest, values)
    if errors:
        raise TemplateError("cosmetic validation failed: " + "; ".join(errors))

    flag_value = _resolve_flag(manifest, values)
    credentials = _credentials_list(manifest, values)
    env_overrides = _env_overrides(manifest, values, flag_value, credentials)
    lab_yaml = render_lab_yaml(manifest, values, flag_value, credentials)

    # Always append a random token so two instances of one template (even with
    # the same company name) never collide on the rendered dir / lab slug, which
    # would otherwise rmtree the first instance and trip the UNIQUE(lab_id) row.
    base = (instance_key or _slugify_company(values.get("company")) or "")[:16]
    base = re.sub(r"[^a-z0-9-]", "", base.lower()).strip("-")
    suffix = f"{base}-{secrets.token_hex(3)}" if base else secrets.token_hex(4)
    dir_name = _rendered_dir_name(manifest, values, suffix)

    archetype = manifest.get("archetype", "linux")
    track_subdir = _TRACK_SUBDIR.get(archetype, archetype.capitalize())
    dest = os.path.join(LABS_DIR, track_subdir, dir_name)

    # Copy the template's container build context + compose, then write lab.yaml.
    # _load_template_yaml(slug) above already validated the slug, but assert the
    # resolved src/dest stay inside their roots so no copytree can ever escape
    # (defence in depth against the path-traversal primitive).
    src = os.path.join(TEMPLATES_DIR, slug)
    _assert_within(src, TEMPLATES_DIR, "template source")
    _assert_within(dest, LABS_DIR, "rendered lab dir")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(
        src, dest,
        ignore=shutil.ignore_patterns("template.yaml", "README.md", "*.pyc", "__pycache__"),
    )

    # Apply the hostname skin to the compose file (display-only).
    _skin_compose(manifest, values, dest)

    with open(os.path.join(dest, "lab.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump(lab_yaml, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return {
        "template_slug": slug,
        "template_version": int(manifest.get("version", 1) or 1),
        "lab_dir": dest,
        "lab_slug": dir_name,
        "track_subdir": track_subdir,
        "flag": flag_value,
        "credentials": credentials,
        "env_overrides": env_overrides,
        "cosmetic_values": values,
        "lab_yaml": lab_yaml,
    }


def _skin_compose(manifest, values, dest):
    """Rewrite the rendered docker-compose.yml hostnames from the skin.

    Maps each topology node's default hostname to the instructor-chosen one. The
    ip_offset labels (structural) are left exactly as the template ships them.
    """
    compose_path = os.path.join(dest, "docker-compose.yml")
    if not os.path.isfile(compose_path):
        return
    try:
        with open(compose_path, encoding="utf-8") as fh:
            compose = yaml.safe_load(fh) or {}
    except yaml.YAMLError:
        return

    new_hosts = _hostnames_for(manifest, values)
    services = compose.get("services", {}) or {}
    # Order services by their ip_offset so hostname index matches topology order.
    ordered = sorted(
        services.items(),
        key=lambda kv: _coerce_offset((kv[1].get("labels", {}) or {}).get("ip_offset", 0)),
    )
    replacements = {}
    for idx, (_svc, body) in enumerate(ordered):
        if idx >= len(new_hosts):
            break
        old = body.get("hostname")
        new = new_hosts[idx]
        if old and new and old != new:
            body["hostname"] = new
            replacements[old] = new

    with open(compose_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(compose, fh, default_flow_style=False, sort_keys=False)

    # Propagate the hostname swap into support scripts/HTML so display strings
    # match (structural logic is untouched: only the old hostname literal moves).
    if replacements:
        for root, _dirs, files in os.walk(dest):
            for name in files:
                if name in ("docker-compose.yml", "lab.yaml"):
                    continue
                fpath = os.path.join(root, name)
                try:
                    with open(fpath, encoding="utf-8") as fh:
                        text = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                skinned = _apply_skin_to_text(text, replacements)
                if skinned != text:
                    with open(fpath, "w", encoding="utf-8") as fh:
                        fh.write(skinned)


# ---------------------------------------------------------------------------
# Ingest (discover_labs as visibility=draft)
# ---------------------------------------------------------------------------

def ingest_draft_lab(lab_slug):
    """Ingest a single materialized lab via the discover_labs machinery.

    Phase 0 instances render with ``visibility: draft`` in their lab.yaml, and
    discover_labs honours the yaml visibility for NEW labs (existing labs keep
    their DB value), so a fresh instance lands as a draft. We run the standard
    discovery so the lab gets the same validation, flag-hash and topology
    handling every other lab gets; nothing instance-specific bypasses it.

    Returns the discover_labs validation status string for the lab, or None if
    the lab row could not be found afterward.
    """
    # Import lazily: discover_labs guards on yaml/sqlalchemy and prints install
    # help if run on a bare host, so importing it at module load would be noisy
    # in non-container contexts.
    from app.scripts import discover_labs as _discover

    _discover.discover_labs()

    # Report back the resulting validation status for the gate to surface.
    from app.database import SessionLocal
    from sqlalchemy import text as _sql_text
    db = SessionLocal()
    try:
        row = db.execute(
            _sql_text("SELECT id, validation_status FROM labs WHERE slug = :slug"),
            {"slug": lab_slug},
        ).fetchone()
        if not row:
            return None
        return {"lab_id": row[0], "validation_status": row[1]}
    finally:
        db.close()
