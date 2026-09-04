#!/usr/bin/env python3
"""
OpenCyberRange - Lab Validator
Validates lab structure, metadata, and configuration before deployment.

Usage:
    python3 scripts/validate-lab.py labs/Windows/windows-1-1-basic-port-scan/
    python3 scripts/validate-lab.py --all
    python3 scripts/validate-lab.py --all --json
"""

import os
import sys
import re
import json
import argparse
import hashlib

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# ── Constants ──────────────────────────────────────────────────────────────

VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced", "expert"}
VALID_CATEGORIES = {
    "assessment", "authentication", "credential-attacks", "crypto",
    "enumeration", "exploitation", "forensics", "general", "network",
    "network-analysis", "post-exploitation", "privesc",
    "privilege-escalation", "reconnaissance", "web",
}
# Standard: {track}-{level}-{lab}-{name}. Midterm: {track}-midterm-{lab}-{name}
# Track prefix may be multi-word (e.g., windows-server).
SLUG_PATTERN = re.compile(r"^[a-z]+(?:-[a-z]+)*-(?:\d+-\d+|midterm-\d+)-[a-z0-9-]+$")
FLAG_PATTERN = re.compile(r"^OCR\{.+\}$")
REQUIRED_YAML_FIELDS = ["name", "description", "difficulty", "flag"]
KNOWN_TRACK_SLUGS = {"windows", "linux", "web", "network", "capitalflow", "forensics", "refinery", "windows-server"}
DANGEROUS_PASSWORD_CHARS = set('!`$\\"')
DANGEROUS_PASSWORD_CHARS_DISPLAY = "! ` $ \\ \""


# ── Result Tracking ───────────────────────────────────────────────────────

class CheckResult:
    def __init__(self, name, passed, message="", severity="error"):
        self.name = name
        self.passed = passed
        self.message = message
        self.severity = severity  # error, warning, info

    def __repr__(self):
        status = "PASS" if self.passed else self.severity.upper()
        line = f"[{status:>7}] {self.name}"
        if self.message:
            line += f"\n          {self.message}"
        return line

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
        }


# ── Validation Checks ─────────────────────────────────────────────────────

def check_required_files(lab_dir):
    """Check that lab.yaml and docker-compose.yml exist."""
    results = []

    yaml_path = os.path.join(lab_dir, "lab.yaml")
    results.append(CheckResult(
        "lab.yaml exists",
        os.path.exists(yaml_path),
        "" if os.path.exists(yaml_path) else f"Missing: {yaml_path}"
    ))

    compose_path = os.path.join(lab_dir, "docker-compose.yml")
    results.append(CheckResult(
        "docker-compose.yml exists",
        os.path.exists(compose_path),
        "" if os.path.exists(compose_path) else f"Missing: {compose_path}"
    ))

    return results


def check_yaml_valid(lab_dir):
    """Check that lab.yaml is valid YAML and has required fields."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return [CheckResult("lab.yaml parseable", False, "File does not exist")]

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [CheckResult("lab.yaml parseable", False, f"YAML parse error: {e}")]

    if not isinstance(data, dict):
        return [CheckResult("lab.yaml parseable", False, "lab.yaml did not parse as a dictionary")]

    results = [CheckResult("lab.yaml parseable", True)]

    # Check required fields
    missing = [f for f in REQUIRED_YAML_FIELDS if f not in data or not data[f]]
    results.append(CheckResult(
        "Required fields present",
        len(missing) == 0,
        f"Missing: {', '.join(missing)}" if missing else ""
    ))

    # Difficulty
    difficulty = data.get("difficulty", "")
    results.append(CheckResult(
        "Valid difficulty",
        difficulty in VALID_DIFFICULTIES,
        f"Got '{difficulty}', expected one of: {', '.join(sorted(VALID_DIFFICULTIES))}" if difficulty not in VALID_DIFFICULTIES else "",
        severity="warning"
    ))

    # Category
    category = data.get("category", "")
    if category:
        results.append(CheckResult(
            "Valid category",
            category in VALID_CATEGORIES,
            f"Got '{category}', expected one of: {', '.join(sorted(VALID_CATEGORIES))}" if category not in VALID_CATEGORIES else "",
            severity="warning"
        ))

    # Flag format
    flag = data.get("flag", "")
    if flag:
        results.append(CheckResult(
            "Flag format OCR{...}",
            bool(FLAG_PATTERN.match(flag)),
            f"Got '{flag}', expected format: OCR{{description}}" if not FLAG_PATTERN.match(flag) else ""
        ))

    # Objectives (accept either 'objectives' or 'learning_objectives')
    objectives = data.get("objectives") or data.get("learning_objectives", [])
    results.append(CheckResult(
        "Has objectives",
        isinstance(objectives, list) and len(objectives) > 0,
        "No objectives defined (use 'objectives' or 'learning_objectives')" if not objectives else "",
        severity="warning"
    ))

    # Duration
    duration = data.get("duration_minutes")
    if duration is not None:
        results.append(CheckResult(
            "Duration is reasonable",
            isinstance(duration, (int, float)) and 10 <= duration <= 300,
            f"Duration is {duration} minutes (expected 10-300)" if not (isinstance(duration, (int, float)) and 10 <= duration <= 300) else "",
            severity="warning"
        ))

    # Hints format
    hints = data.get("hints", [])
    if hints and isinstance(hints, list):
        # Check if hints use structured format
        for i, hint in enumerate(hints):
            if isinstance(hint, dict):
                if "text" not in hint and "content" not in hint:
                    results.append(CheckResult(
                        f"Hint {i+1} has text/content",
                        False,
                        f"Hint {i+1} is a dict but has no 'text' or 'content' key",
                        severity="warning"
                    ))

    return results


def extract_track_from_slug(slug):
    """Extract the track prefix from a lab slug.

    Tries longest known track first so 'windows-server-1-1-...' matches
    'windows-server' rather than 'windows'.  Falls back to the first
    word if no known track matches.
    """
    for track in sorted(KNOWN_TRACK_SLUGS, key=len, reverse=True):
        prefix = track + "-"
        if slug.startswith(prefix):
            remainder = slug[len(prefix):]
            # Remainder must start with digits (level) or 'midterm'
            if re.match(r"^(\d+|midterm)-", remainder):
                return track
    return slug.split("-")[0]


def check_slug_format(lab_dir):
    """Check that the directory name follows the slug convention."""
    slug = os.path.basename(os.path.normpath(lab_dir))

    results = []

    if SLUG_PATTERN.match(slug):
        results.append(CheckResult("Slug format valid", True))

        # Extract track from slug and check it's known
        track = extract_track_from_slug(slug)
        results.append(CheckResult(
            "Track slug recognized",
            track in KNOWN_TRACK_SLUGS,
            f"Track '{track}' not in known tracks: {', '.join(sorted(KNOWN_TRACK_SLUGS))}" if track not in KNOWN_TRACK_SLUGS else "",
            severity="warning"
        ))
    else:
        results.append(CheckResult(
            "Slug format valid",
            False,
            f"Got '{slug}', expected: {{track}}-{{level}}-{{lab}}-{{name}} (e.g., windows-1-1-basic-port-scan) or {{track}}-midterm-{{lab}}-{{name}} (e.g., windows-midterm-1-network-enumeration-assessment)"
        ))

    return results


def check_compose_valid(lab_dir):
    """Check docker-compose.yml structure."""
    compose_path = os.path.join(lab_dir, "docker-compose.yml")
    if not os.path.exists(compose_path):
        return []

    try:
        with open(compose_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [CheckResult("docker-compose.yml parseable", False, f"YAML parse error: {e}")]

    if not isinstance(data, dict):
        return [CheckResult("docker-compose.yml parseable", False, "Did not parse as a dictionary")]

    results = [CheckResult("docker-compose.yml parseable", True)]

    # Warn about deprecated version field
    if "version" in data:
        results.append(CheckResult(
            "No deprecated 'version' field",
            False,
            "Remove 'version' field - it's deprecated in modern Docker Compose",
            severity="warning"
        ))

    # Warn about network definitions (platform handles networking)
    if "networks" in data:
        results.append(CheckResult(
            "No 'networks' section",
            False,
            "Remove 'networks' section - the platform manages lab networking automatically",
            severity="warning"
        ))

    # Check services
    services = data.get("services", {})
    has_shared = "x-ocr-shared-containers" in data
    if not services:
        if has_shared:
            results.append(CheckResult("Has services defined", True,
                "No local services — uses shared containers (x-ocr-shared-containers)"))
        else:
            results.append(CheckResult("Has services defined", False, "No services in docker-compose.yml"))
        return results

    results.append(CheckResult("Has services defined", True))

    # Check each service for ip_offset label
    for svc_name, svc_config in services.items():
        if not isinstance(svc_config, dict):
            continue

        labels = svc_config.get("labels", {})
        has_offset = False
        if isinstance(labels, dict):
            has_offset = "ip_offset" in labels
        elif isinstance(labels, list):
            has_offset = any("ip_offset" in str(l) for l in labels)

        results.append(CheckResult(
            f"Service '{svc_name}' has ip_offset label",
            has_offset,
            f"Add 'labels: ip_offset: \"10\"' to service '{svc_name}' for network assignment" if not has_offset else ""
        ))

        # Check for build context
        build = svc_config.get("build")
        if build:
            if isinstance(build, str):
                build_context = build
            elif isinstance(build, dict):
                build_context = build.get("context", ".")
            else:
                build_context = "."

            dockerfile_path = os.path.join(lab_dir, build_context, "Dockerfile")
            if not isinstance(build, dict) or "dockerfile" not in build:
                pass  # default Dockerfile name
            else:
                dockerfile_path = os.path.join(lab_dir, build_context, build["dockerfile"])

            results.append(CheckResult(
                f"Service '{svc_name}' Dockerfile exists",
                os.path.exists(dockerfile_path),
                f"Missing: {dockerfile_path}" if not os.path.exists(dockerfile_path) else ""
            ))

        # Check for resource limits
        deploy = svc_config.get("deploy", {})
        has_limits = bool(deploy.get("resources", {}).get("limits"))
        results.append(CheckResult(
            f"Service '{svc_name}' has resource limits",
            has_limits,
            "Consider adding deploy.resources.limits (cpus, memory) to prevent resource exhaustion",
            severity="info"
        ))

    return results


def check_flag_consistency(lab_dir):
    """Check that the flag in lab.yaml matches what's in the Dockerfile(s)."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []

    yaml_flag = data.get("flag", "")
    if not yaml_flag:
        return []

    results = []

    # Search all container files for the flag (Dockerfiles, app code, configs, HTML)
    # Flags can be in Dockerfiles, Python apps, HTML files, config files, etc.
    SEARCHABLE_EXTENSIONS = {
        ".py", ".html", ".htm", ".js", ".php", ".conf", ".cfg", ".txt",
        ".sh", ".bash", ".yml", ".yaml", ".json", ".xml", ".sql", ".env",
        ".rb", ".pl", ".go", ".java", ".c", ".cpp", ".rs",
        "",  # Dockerfile has no extension
    }

    searchable_files = []
    dockerfiles = []
    for root, dirs, files in os.walk(lab_dir):
        for f in files:
            fpath = os.path.join(root, f)
            _, ext = os.path.splitext(f)
            if f == "Dockerfile":
                dockerfiles.append(fpath)
                searchable_files.append(fpath)
            elif ext.lower() in SEARCHABLE_EXTENSIONS:
                searchable_files.append(fpath)

    if not dockerfiles:
        # Check if this lab uses shared containers (no local Dockerfiles expected)
        compose_path = os.path.join(lab_dir, "docker-compose.yml")
        uses_shared = False
        if os.path.exists(compose_path):
            try:
                with open(compose_path, "r") as f:
                    compose_data = yaml.safe_load(f)
                uses_shared = isinstance(compose_data, dict) and "x-ocr-shared-containers" in compose_data
            except (yaml.YAMLError, IOError):
                pass
        if uses_shared:
            results.append(CheckResult(
                "Dockerfiles found",
                True,
                "No local Dockerfiles — uses shared containers"
            ))
        else:
            results.append(CheckResult(
                "Dockerfiles found",
                False,
                "No Dockerfiles found in lab directory"
            ))
        return results

    # Check all container files for the flag
    flag_found_in_any = False
    for fpath in searchable_files:
        try:
            with open(fpath, "r", errors="ignore") as f:
                content = f.read()
            if yaml_flag in content:
                flag_found_in_any = True
                break
        except IOError:
            pass

    results.append(CheckResult(
        "Flag in lab.yaml found in container files",
        flag_found_in_any,
        f"Flag '{yaml_flag}' not found in any container file (Dockerfiles, scripts, HTML, etc.). Ensure the flag in lab.yaml matches exactly." if not flag_found_in_any else ""
    ))

    # Check for DEBIAN_FRONTEND in Dockerfiles
    for df_path in dockerfiles:
        rel_path = os.path.relpath(df_path, lab_dir)
        try:
            with open(df_path, "r") as f:
                content = f.read()
            has_noninteractive = "DEBIAN_FRONTEND=noninteractive" in content
            # Only warn for ubuntu/debian based images
            if "FROM ubuntu" in content or "FROM debian" in content:
                results.append(CheckResult(
                    f"{rel_path} has DEBIAN_FRONTEND=noninteractive",
                    has_noninteractive,
                    "Ubuntu/Debian images should set ENV DEBIAN_FRONTEND=noninteractive to prevent build hangs",
                    severity="warning"
                ))
        except IOError:
            pass

    return results


def check_hint_flag_leaks(lab_dir):
    """Check that hints don't give away the flag value."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []

    flag = data.get("flag", "")
    hints = data.get("hints", [])
    if not flag or not hints:
        return []

    results = []
    # Check each hint for the flag value
    for i, hint in enumerate(hints):
        hint_text = ""
        if isinstance(hint, str):
            hint_text = hint
        elif isinstance(hint, dict):
            hint_text = hint.get("text", "") or hint.get("content", "")

        if flag in hint_text:
            results.append(CheckResult(
                f"Hint {i+1} does not reveal the flag",
                False,
                f"Hint {i+1} contains the actual flag value '{flag}'. "
                "Hints should guide students toward the solution without giving away the answer. "
                "Use OCR{{...}} as a placeholder instead.",
                severity="error"
            ))

    if not results:
        results.append(CheckResult(
            "Hints do not reveal flag values",
            True,
            ""
        ))

    return results


def check_track_placement(lab_dir):
    """Check that the lab is in the correct track directory."""
    slug = os.path.basename(os.path.normpath(lab_dir))
    parent = os.path.basename(os.path.dirname(os.path.normpath(lab_dir)))

    if not SLUG_PATTERN.match(slug):
        return []

    track_from_slug = extract_track_from_slug(slug)

    # Map track slugs to expected directory names
    expected_dirs = {
        "windows": "Windows",
        "windows-server": "Windows Server",
        "linux": "Linux",
        "web": "Web",
        "network": "Network",
        "capitalflow": "Capital Flow",
        "forensics": "Forensics",
        "refinery": "Refinery",
    }

    expected_dir = expected_dirs.get(track_from_slug, "")
    if not expected_dir:
        return []

    matches = parent.lower().replace(" ", "") == expected_dir.lower().replace(" ", "")
    return [CheckResult(
        "Lab in correct track directory",
        matches,
        f"Lab slug starts with '{track_from_slug}' but is in directory '{parent}' (expected '{expected_dir}')" if not matches else "",
        severity="warning"
    )]


# ── Anti-Pattern Checks ──────────────────────────────────────────────────

def check_password_safety(lab_dir):
    """Check that credentials passwords don't contain shell-dangerous characters."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []

    credentials = data.get("credentials", [])
    if not credentials:
        return []

    results = []
    for cred in credentials:
        password = cred.get("password", "")
        role = cred.get("role", "unknown")
        bad_chars = [c for c in password if c in DANGEROUS_PASSWORD_CHARS]
        if bad_chars:
            results.append(CheckResult(
                f"Password safe for role '{role}'",
                False,
                f"Password contains dangerous character(s): {' '.join(repr(c) for c in bad_chars)}. "
                f"These cause failures through shell quoting layers (Dockerfile RUN, sshpass, bash -c). "
                f"Use only: # _ - @ . % ^ + ="
            ))
        else:
            results.append(CheckResult(f"Password safe for role '{role}'", True))

    return results


def check_command_antipatterns(lab_dir):
    """Check test step commands for known anti-patterns that cause failures."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []

    steps = data.get("test", {}).get("steps", [])
    if not steps:
        return []

    results = []
    for i, step in enumerate(steps):
        cmd = step.get("command", "")
        step_name = step.get("name", f"step {i+1}")

        # Check for -X POST combined with -L (follow redirects)
        if re.search(r"-X\s+POST", cmd) and "-L" in cmd:
            results.append(CheckResult(
                f"No -X POST + -L in '{step_name}'",
                False,
                "curl -X POST forces POST on redirect targets (405 errors). "
                "Remove -X POST; -d alone implies POST and properly switches to GET on redirects.",
                severity="error"
            ))

        # Check for grep -P (PCRE) — not portable
        if re.search(r"grep\s+(-\w*P|--perl-regexp)", cmd):
            results.append(CheckResult(
                f"No grep -P in '{step_name}'",
                False,
                "grep -P (Perl regex) is not available in BusyBox/Alpine. "
                "Use grep -o 'pattern' | cut or grep -E instead.",
                severity="error"
            ))

        # Check for != in commands (bash ! expansion risk)
        if "!=" in cmd and ("jq" in cmd or "select" in cmd):
            results.append(CheckResult(
                f"No != in jq expression in '{step_name}'",
                False,
                "The ! character in != triggers bash history expansion through "
                "shell wrapping layers. Use select(.field) instead of select(.field != null).",
                severity="error"
            ))

        # Warn about 2>/dev/null (hides errors)
        if "2>/dev/null" in cmd and "2>&1" not in cmd:
            results.append(CheckResult(
                f"stderr visible in '{step_name}'",
                False,
                "2>/dev/null hides error messages (auth failures, permission denied, missing tools). "
                "Consider using 2>&1 instead so errors are visible for diagnostics.",
                severity="warning"
            ))

    if not results:
        results.append(CheckResult("Test commands free of anti-patterns", True))

    return results


def check_template_resolution(lab_dir):
    """Verify every {target.X} and {cred.X.user/pass} in test steps has a matching source."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []

    steps = data.get("test", {}).get("steps", [])
    if not steps:
        return []

    # Collect valid node IDs from topology
    node_ids = set()
    for node in data.get("topology", {}).get("nodes", []):
        if node.get("id"):
            node_ids.add(node["id"])

    # Also accept docker-compose service names and shared container aliases as valid targets
    compose_path = os.path.join(lab_dir, "docker-compose.yml")
    if os.path.exists(compose_path):
        try:
            with open(compose_path, "r") as f:
                compose = yaml.safe_load(f) or {}
            for svc_name in compose.get("services", {}).keys():
                node_ids.add(svc_name)
            # Read x-ocr-shared-containers aliases (shared VM/container references)
            for shared in compose.get("x-ocr-shared-containers", []):
                if isinstance(shared, dict):
                    # The container name itself
                    if shared.get("name"):
                        node_ids.add(shared["name"])
                    # Aliases are the names test steps typically reference
                    for alias in shared.get("aliases", []):
                        node_ids.add(alias)
        except (yaml.YAMLError, IOError):
            pass

    # Collect valid credential roles
    cred_roles = set()
    for cred in data.get("credentials", []):
        if cred.get("role"):
            cred_roles.add(cred["role"])

    results = []
    for i, step in enumerate(steps):
        cmd = step.get("command", "")
        step_name = step.get("name", f"step {i+1}")

        # Find all {target.X} references
        for m in re.finditer(r"\{target\.([^}]+)\}", cmd):
            target_id = m.group(1)
            if target_id not in node_ids:
                results.append(CheckResult(
                    f"Template {{target.{target_id}}} resolves in '{step_name}'",
                    False,
                    f"No topology node or docker-compose service named '{target_id}'. "
                    f"Available: {', '.join(sorted(node_ids)) if node_ids else '(none — add topology or docker-compose services)'}"
                ))

        # Find all {cred.X.user} and {cred.X.pass} references
        for m in re.finditer(r"\{cred\.([^.}]+)\.(user|pass)\}", cmd):
            role = m.group(1)
            field = m.group(2)
            if role not in cred_roles:
                results.append(CheckResult(
                    f"Template {{cred.{role}.{field}}} resolves in '{step_name}'",
                    False,
                    f"No credential with role '{role}'. "
                    f"Available roles: {', '.join(sorted(cred_roles)) if cred_roles else '(none — add credentials section)'}"
                ))

    if not results:
        results.append(CheckResult("All template variables resolve", True))

    return results


def check_mysql_auth_plugin(lab_dir):
    """Check Dockerfiles and SQL files for MySQL users without mysql_native_password."""
    results = []
    create_user_pattern = re.compile(
        r"CREATE\s+USER.*IDENTIFIED\s+BY\s+",
        re.IGNORECASE
    )
    native_password_pattern = re.compile(
        r"IDENTIFIED\s+WITH\s+mysql_native_password\s+BY",
        re.IGNORECASE
    )
    # Check if any MySQL 8 image is used
    mysql8_used = False
    for root, dirs, files in os.walk(lab_dir):
        for f in files:
            fpath = os.path.join(root, f)
            if f in ("Dockerfile", "docker-compose.yml"):
                try:
                    with open(fpath, "r", errors="ignore") as fh:
                        content = fh.read()
                    if "mysql:8" in content.lower() or "mysql:latest" in content.lower():
                        mysql8_used = True
                except IOError:
                    pass

    if not mysql8_used:
        return []

    for root, dirs, files in os.walk(lab_dir):
        for f in files:
            fpath = os.path.join(root, f)
            _, ext = os.path.splitext(f)
            if ext.lower() in (".sql", "") or f == "Dockerfile":
                try:
                    with open(fpath, "r", errors="ignore") as fh:
                        content = fh.read()
                except IOError:
                    continue

                # Find CREATE USER ... IDENTIFIED BY without mysql_native_password
                for m in create_user_pattern.finditer(content):
                    line = content[max(0, m.start()-20):m.end()+80]
                    if not native_password_pattern.search(line):
                        rel = os.path.relpath(fpath, lab_dir)
                        results.append(CheckResult(
                            f"MySQL auth plugin in {rel}",
                            False,
                            "MySQL 8.0 CREATE USER without mysql_native_password. "
                            "The tester sidecar uses mariadb-client which doesn't support "
                            "caching_sha2_password. Use: IDENTIFIED WITH mysql_native_password BY '...'",
                            severity="error"
                        ))

    if mysql8_used and not results:
        results.append(CheckResult("MySQL auth plugin compatible", True))

    return results


def check_topology_ip_offset_match(lab_dir):
    """Verify topology node ip_offset values match docker-compose service labels."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    compose_path = os.path.join(lab_dir, "docker-compose.yml")
    if not os.path.exists(yaml_path) or not os.path.exists(compose_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            lab_data = yaml.safe_load(f) or {}
        with open(compose_path, "r") as f:
            compose_data = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return []

    topo_nodes = lab_data.get("topology", {}).get("nodes", [])
    services = compose_data.get("services", {})
    if not topo_nodes or not services:
        return []

    # Build service → ip_offset map from docker-compose
    compose_offsets = {}
    for svc_name, svc_def in services.items():
        if not isinstance(svc_def, dict):
            continue
        labels = svc_def.get("labels", {})
        if isinstance(labels, list):
            label_dict = {}
            for item in labels:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    label_dict[k.strip()] = v.strip()
            labels = label_dict
        if "ip_offset" in labels:
            compose_offsets[svc_name] = str(labels["ip_offset"])

    results = []
    for node in topo_nodes:
        node_id = node.get("id", "")
        node_offset = str(node.get("ip_offset", ""))
        if not node_offset or node_id == "attacker":
            continue

        # Check if this offset exists in any compose service
        matching_services = [s for s, o in compose_offsets.items() if o == node_offset]
        if not matching_services:
            results.append(CheckResult(
                f"Topology node '{node_id}' ip_offset matches compose",
                False,
                f"Node '{node_id}' has ip_offset={node_offset} but no docker-compose service "
                f"has that offset. Available: {compose_offsets}",
                severity="error"
            ))

    if not results and topo_nodes:
        results.append(CheckResult("Topology ip_offsets match docker-compose", True))

    return results


def check_test_steps_exist(lab_dir):
    """Warn if no test steps are defined."""
    yaml_path = os.path.join(lab_dir, "lab.yaml")
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []

    steps = data.get("test", {}).get("steps", [])
    flag = data.get("flag", "")

    if flag and not steps:
        return [CheckResult(
            "Test steps defined",
            False,
            "Lab has a flag but no test: steps. The exercise cannot be fully validated. "
            "Add test steps that walk through the solve path and output the flag.",
            severity="warning"
        )]

    if steps:
        # Check that last step expects the flag
        last_step = steps[-1]
        expect = last_step.get("expect", "")
        cmd = last_step.get("command", "")
        if flag and "OCR{" not in expect and "OCR{" not in cmd and "OCR" not in expect:
            return [CheckResult(
                "Last test step retrieves flag",
                False,
                "Last test step does not appear to retrieve the flag. "
                "The final step should have expect: \"OCR{\" or output the flag string.",
                severity="warning"
            )]

    return []


def check_dockerfile_password_safety(lab_dir):
    """Scan Dockerfiles and shell scripts for passwords with dangerous characters."""
    results = []
    chpasswd_pattern = re.compile(r"echo\s+['\"](\w+):([^'\"]+)['\"]\s*\|\s*chpasswd")

    for root, dirs, files in os.walk(lab_dir):
        for f in files:
            _, ext = os.path.splitext(f)
            if f == "Dockerfile" or ext in (".sh", ".bash"):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, "r", errors="ignore") as fh:
                        content = fh.read()
                except IOError:
                    continue

                for m in chpasswd_pattern.finditer(content):
                    user = m.group(1)
                    password = m.group(2)
                    bad_chars = [c for c in password if c in DANGEROUS_PASSWORD_CHARS]
                    if bad_chars:
                        rel = os.path.relpath(fpath, lab_dir)
                        results.append(CheckResult(
                            f"Dockerfile password safe for '{user}' in {rel}",
                            False,
                            f"Password for '{user}' contains dangerous character(s): "
                            f"{' '.join(repr(c) for c in bad_chars)}. "
                            f"These cause failures through shell quoting layers. "
                            f"Use only: # _ - @ . % ^ + =",
                            severity="error"
                        ))

    return results


# ── Main Validation Runner ────────────────────────────────────────────────

def validate_lab(lab_dir):
    """Run all checks on a lab directory. Returns list of CheckResults."""
    lab_dir = os.path.normpath(lab_dir)

    if not os.path.isdir(lab_dir):
        return [CheckResult("Lab directory exists", False, f"Not a directory: {lab_dir}")]

    results = []
    results.extend(check_required_files(lab_dir))
    results.extend(check_yaml_valid(lab_dir))
    results.extend(check_slug_format(lab_dir))
    results.extend(check_compose_valid(lab_dir))
    results.extend(check_flag_consistency(lab_dir))
    results.extend(check_hint_flag_leaks(lab_dir))
    results.extend(check_track_placement(lab_dir))
    # Anti-pattern checks
    results.extend(check_password_safety(lab_dir))
    results.extend(check_dockerfile_password_safety(lab_dir))
    results.extend(check_command_antipatterns(lab_dir))
    results.extend(check_template_resolution(lab_dir))
    results.extend(check_mysql_auth_plugin(lab_dir))
    results.extend(check_topology_ip_offset_match(lab_dir))
    results.extend(check_test_steps_exist(lab_dir))

    return results


def find_all_labs(labs_dir):
    """Find all lab directories under the labs/ root."""
    labs = []
    if not os.path.isdir(labs_dir):
        return labs

    for track_name in sorted(os.listdir(labs_dir)):
        track_path = os.path.join(labs_dir, track_name)
        if not os.path.isdir(track_path) or track_name.startswith("."):
            continue

        for lab_name in sorted(os.listdir(track_path)):
            lab_path = os.path.join(track_path, lab_name)
            if not os.path.isdir(lab_path) or lab_name.startswith("."):
                continue

            # Must have at least lab.yaml or docker-compose.yml
            if os.path.exists(os.path.join(lab_path, "lab.yaml")) or \
               os.path.exists(os.path.join(lab_path, "docker-compose.yml")):
                labs.append(lab_path)

    return labs


def print_results(lab_dir, results, verbose=False):
    """Print results for a single lab."""
    slug = os.path.basename(os.path.normpath(lab_dir))
    errors = [r for r in results if not r.passed and r.severity == "error"]
    warnings = [r for r in results if not r.passed and r.severity == "warning"]
    infos = [r for r in results if not r.passed and r.severity == "info"]
    passed = [r for r in results if r.passed]

    # Header
    total_checks = len(results)
    pass_count = len(passed)

    if errors:
        status = f"\033[0;31mFAIL\033[0m"
    elif warnings:
        status = f"\033[1;33mWARN\033[0m"
    else:
        status = f"\033[0;32mOK\033[0m"

    print(f"\n{'─' * 60}")
    print(f"  {slug}  [{status}]  {pass_count}/{total_checks} checks passed")
    print(f"{'─' * 60}")

    if verbose:
        for r in results:
            print(f"  {r}")
    else:
        # Only show failures
        for r in errors + warnings:
            print(f"  {r}")
        if infos and verbose:
            for r in infos:
                print(f"  {r}")

    return len(errors)


def main():
    parser = argparse.ArgumentParser(
        description="Validate OpenCyberRange structure and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s labs/Windows/windows-1-1-basic-port-scan/
  %(prog)s --all
  %(prog)s --all --verbose
  %(prog)s --all --json
  %(prog)s --all --summary
        """
    )

    parser.add_argument("lab_dir", nargs="?", help="Path to a specific lab directory")
    parser.add_argument("--all", action="store_true", help="Validate all labs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all checks including passing ones")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--summary", action="store_true", help="Only show summary counts")
    parser.add_argument("--labs-dir", default=None, help="Labs root directory (default: auto-detect)")

    args = parser.parse_args()

    if not args.lab_dir and not args.all:
        parser.print_help()
        sys.exit(1)

    # Find labs root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    labs_dir = args.labs_dir or os.path.join(project_root, "labs")

    if args.all:
        lab_dirs = find_all_labs(labs_dir)
        if not lab_dirs:
            print(f"No labs found in {labs_dir}")
            sys.exit(1)
    else:
        lab_dirs = [args.lab_dir]

    # Run validation
    all_results = {}
    total_errors = 0
    total_warnings = 0
    total_labs = len(lab_dirs)

    for lab_dir in lab_dirs:
        results = validate_lab(lab_dir)
        all_results[lab_dir] = results

        errors = [r for r in results if not r.passed and r.severity == "error"]
        warnings = [r for r in results if not r.passed and r.severity == "warning"]
        total_errors += len(errors)
        total_warnings += len(warnings)

    # Output
    if args.json:
        output = {}
        for lab_dir, results in all_results.items():
            slug = os.path.basename(os.path.normpath(lab_dir))
            output[slug] = {
                "path": lab_dir,
                "checks": [r.to_dict() for r in results],
                "errors": sum(1 for r in results if not r.passed and r.severity == "error"),
                "warnings": sum(1 for r in results if not r.passed and r.severity == "warning"),
            }
        output["_summary"] = {
            "total_labs": total_labs,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
        }
        print(json.dumps(output, indent=2))
    elif args.summary:
        labs_with_errors = sum(
            1 for results in all_results.values()
            if any(not r.passed and r.severity == "error" for r in results)
        )
        labs_with_warnings = sum(
            1 for results in all_results.values()
            if any(not r.passed and r.severity == "warning" for r in results)
        )
        labs_clean = total_labs - labs_with_errors - labs_with_warnings

        print(f"\n  Labs validated:  {total_labs}")
        print(f"  \033[0;32mClean:\033[0m          {labs_clean}")
        print(f"  \033[1;33mWarnings:\033[0m       {labs_with_warnings}")
        print(f"  \033[0;31mErrors:\033[0m         {labs_with_errors}")
        print(f"  Total errors:    {total_errors}")
        print(f"  Total warnings:  {total_warnings}")
    else:
        for lab_dir, results in all_results.items():
            print_results(lab_dir, results, verbose=args.verbose)

        # Final summary
        if total_labs > 1:
            print(f"\n{'═' * 60}")
            print(f"  Summary: {total_labs} labs, {total_errors} errors, {total_warnings} warnings")
            print(f"{'═' * 60}")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
