"""
Exercise Tester — automated end-to-end lab validation.

Spawns a lab environment, attaches a lightweight tester sidecar container
with pentesting tools (nmap, curl, ftp, nc), runs connectivity / port-scan /
service-banner / custom-solve steps, validates flag retrieval, and cleans up.

Results are streamed as Server-Sent Events (SSE) in the same wire format used
by the Diagnostics suite so the Admin UI terminal can render them identically.
"""

import asyncio
import hashlib
import hmac
import io
import json
import logging
import os
import re
import shlex
import time
import uuid
import yaml
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import requests as http_requests

from app.auth import get_current_admin_user, get_current_instructor_user, create_access_token
from app.config import settings
from app.database import get_db
from app.models import Lab, LabSession, User, FlagAttempt, LabCompletion, ExerciseTestResult, Course, CourseLabAssignment
from app.services.docker_manager import DockerManager, get_subnet_id, get_track_directory_name

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

docker_manager = DockerManager()

# ── Timezone helper ────────────────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo(os.environ.get("TZ", "America/Chicago"))

# ── Constants ──────────────────────────────────────────────────────────────
TESTER_IMAGE = "ocr-tester:latest"
TESTER_USER_ID = 249          # Dedicated test-harness user
DEFAULT_TIMEOUT = 300         # Per-lab timeout (seconds)
CONTAINER_INIT_WAIT = 20      # Seconds to wait after spawning lab
SIDECAR_INIT_WAIT = 2         # Seconds after attaching sidecar to network
EXEC_TIMEOUT = 20             # Default per-command timeout
SSE_HEARTBEAT = ": heartbeat\n\n"  # SSE comment to keep connection alive

# Characters that cause shell quoting failures through the exec chain
DANGEROUS_PASSWORD_CHARS = set('!`$\\"')

# Common stderr patterns mapped to actionable diagnostic hints
ERROR_PATTERN_HINTS = {
    "caching_sha2_password": (
        "MySQL 8.0 auth plugin issue -- use IDENTIFIED WITH mysql_native_password "
        "in CREATE USER statements (the tester sidecar uses mariadb-client)"
    ),
    "Permission denied": (
        "File permission issue -- check group memberships (e.g., add user to 'adm' "
        "group with useradd -G adm for nginx/Apache log access)"
    ),
    "command not found": (
        "Tool not available in tester sidecar -- add it to test.tools in lab.yaml "
        "for auto-install, or verify the command exists on the target container"
    ),
    "Connection refused": (
        "Service not listening -- check that the container CMD runs the service in "
        "foreground mode (e.g., nginx -g 'daemon off;', sshd -D, smbd -F)"
    ),
    "Host is down": (
        "Container may have crashed -- check Docker logs and verify the startup "
        "command doesn't exit prematurely"
    ),
    "Connection timed out": (
        "Network connectivity issue -- verify ip_offset labels match topology and "
        "that containers are on the same lab network"
    ),
    "Name or service not known": (
        "DNS resolution failed -- use IP addresses from {target.X} template "
        "variables instead of hostnames for test step commands"
    ),
}


async def _run_blocking(func, *args, **kwargs):
    """Run a blocking function in a thread so it doesn't stall the SSE stream."""
    return await asyncio.to_thread(func, *args, **kwargs)


# ── Cancellation support ──────────────────────────────────────────────────
_cancel_events: Dict[str, asyncio.Event] = {}

# ── In-memory run state (survives page refresh, cleared on completion) ────
# Keyed by run_id.  Each entry is a dict with:
#   status: "running" | "completed" | "cancelled"
#   total_labs: int
#   labs_completed: int
#   current_lab: str | None          (slug currently being tested)
#   current_lab_name: str | None
#   started_at: str                  (HH:MM:SS)
#   events: list[dict]               (all SSE-style event dicts, in order)
#   summary: dict | None             (set when complete)
#   admin_id: int
#   lab_slugs: list[str]
_active_runs: Dict[str, dict] = {}
MAX_RUN_EVENTS = 50_000              # Cap events per run to bound memory

# ── File-based run state (multi-worker safe) ──────────────────────────────
# uvicorn runs many workers; the POST that starts a run and the GET polls for
# its events land on different worker processes, so in-memory _active_runs is
# invisible to the polling worker. Persist run state to a shared /tmp dir
# (same container, all workers) so any worker can read it. Mirrors the
_RUN_DIR = "/tmp/ocr_exercise_test"
_RUN_TTL_SECONDS = 6 * 3600          # prune run files older than this


def _run_state_path(run_id: str) -> str:
    return os.path.join(_RUN_DIR, f"{run_id}_state.json")


def _run_events_path(run_id: str) -> str:
    return os.path.join(_RUN_DIR, f"{run_id}_events.jsonl")


def _run_cancel_path(run_id: str) -> str:
    return os.path.join(_RUN_DIR, f"{run_id}_cancel")


def _run_write_state(run_id: str, state: dict) -> None:
    os.makedirs(_RUN_DIR, exist_ok=True)
    path = _run_state_path(run_id)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, path)   # atomic on the same filesystem


def _run_read_state(run_id: str):
    try:
        with open(_run_state_path(run_id), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _run_append_event(run_id: str, event: dict) -> None:
    os.makedirs(_RUN_DIR, exist_ok=True)
    with open(_run_events_path(run_id), "a") as f:
        f.write(json.dumps(event) + "\n")


def _run_read_events(run_id: str, after: int = 0):
    """Return (events_slice, total_count). Only newline-terminated lines count,
    so a partial final line written by a concurrent append is ignored until the
    next poll (keeps `after` offsets index-aligned)."""
    try:
        with open(_run_events_path(run_id), "r") as f:
            raw = f.readlines()
    except FileNotFoundError:
        return [], 0
    parsed = []
    for line in raw:
        if not line.endswith("\n"):
            break   # partial final line mid-append; pick it up next poll
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            break
    return parsed[after:], len(parsed)


def _run_is_cancelled(run_id: str) -> bool:
    return os.path.exists(_run_cancel_path(run_id))


def _run_request_cancel(run_id: str) -> bool:
    if _run_read_state(run_id) is None:
        return False
    os.makedirs(_RUN_DIR, exist_ok=True)
    open(_run_cancel_path(run_id), "w").close()
    return True


def _prune_old_runs() -> None:
    """Best-effort cleanup of run files past their TTL so /tmp does not grow."""
    try:
        names = os.listdir(_RUN_DIR)
    except FileNotFoundError:
        return
    cutoff = time.time() - _RUN_TTL_SECONDS
    for name in names:
        path = os.path.join(_RUN_DIR, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


# ── Data helpers ───────────────────────────────────────────────────────────

@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


def _ts() -> str:
    return datetime.now(LOCAL_TZ).strftime("%H:%M:%S")


def _ev(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _load_lab_yaml(lab_slug: str) -> dict:
    """Read lab.yaml from /labs/{Track}/{slug}/lab.yaml.

    Returns {} on a missing, unreadable, or unparseable file so one bad
    lab.yaml cannot 500 callers that scan every lab (e.g. the tester listing).
    """
    track_slug = lab_slug.split("-")[0].lower()
    track_dir = get_track_directory_name(track_slug)
    yaml_path = f"/labs/{track_dir}/{lab_slug}/lab.yaml"
    if not os.path.isfile(yaml_path):
        return {}
    try:
        with open(yaml_path, "r") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("Skipping malformed lab.yaml for %s (%s): %s", lab_slug, yaml_path, exc)
        return {}


def _load_compose_yaml(lab_slug: str) -> dict:
    """Read docker-compose.yml from /labs/{Track}/{slug}/docker-compose.yml.

    Returns {} on a missing, unreadable, or unparseable file so one bad
    compose file cannot 500 callers that scan every lab.
    """
    track_slug = lab_slug.split("-")[0].lower()
    track_dir = get_track_directory_name(track_slug)
    compose_path = f"/labs/{track_dir}/{lab_slug}/docker-compose.yml"
    if not os.path.isfile(compose_path):
        return {}
    try:
        with open(compose_path, "r") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("Skipping malformed docker-compose.yml for %s (%s): %s", lab_slug, compose_path, exc)
        return {}


def _exec_in_tester_sync(container, command: str, timeout: int = EXEC_TIMEOUT) -> ExecResult:
    """Run a command inside the tester sidecar (blocking), return structured result."""
    try:
        exit_code, output = container.exec_run(
            ["bash", "-c", f"timeout {timeout} bash -c {shlex.quote(command)}"],
            demux=True,
        )
        stdout = (output[0] or b"").decode(errors="replace")
        stderr = (output[1] or b"").decode(errors="replace")
        return ExecResult(exit_code=exit_code, stdout=stdout, stderr=stderr)
    except Exception as e:
        return ExecResult(exit_code=-1, stdout="", stderr=str(e))


async def _exec_in_tester(container, command: str, timeout: int = EXEC_TIMEOUT) -> ExecResult:
    """Async wrapper — runs exec in a thread to avoid blocking the SSE stream."""
    return await _run_blocking(_exec_in_tester_sync, container, command, timeout)


def _resolve_template(
    command: str,
    node_ip_map: Dict[str, str],
    subnet: str,
    credentials: List[dict],
) -> str:
    """Replace {target.X}, {subnet}, {cred.role.user/pass} in a command."""
    for node_id, ip in node_ip_map.items():
        command = command.replace(f"{{target.{node_id}}}", ip)
    command = command.replace("{subnet}", subnet)
    for cred in credentials:
        role = cred.get("role", "")
        command = command.replace(f"{{cred.{role}.user}}", cred.get("username", ""))
        command = command.replace(f"{{cred.{role}.pass}}", cred.get("password", ""))
    return command


def _call_submit_flag_api(lab_id: int, flag: str, token: str) -> dict:
    """Call the real POST /api/labs/{lab_id}/submit-flag endpoint via HTTP.

    This tests the full flag engine: auth, rate limit, hash comparison,
    FlagAttempt logging, LabCompletion creation, achievement awards,
    activity logging, and auto-stop — exactly what a student hits.
    """
    try:
        resp = http_requests.post(
            f"http://localhost:8000/api/exercises/labs/{lab_id}/submit-flag",
            json={"flag": flag},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        return {"status_code": resp.status_code, "body": body}
    except Exception as e:
        return {"status_code": -1, "body": {"error": str(e)}}


def _cleanup_stale_images(slug: str, user_id: int) -> list:
    """Remove cached lab images so Dockerfiles are rebuilt from scratch.

    Returns list of removed image tags for logging.
    """
    import docker as docker_lib
    try:
        dclient = docker_lib.from_env()
    except Exception:
        return []

    removed = []
    prefix = f"lab_{user_id}_{slug}"

    for img in dclient.images.list(all=True):
        for tag in (img.tags or []):
            if tag.startswith(prefix) or tag.startswith(f"prebuild-{slug}"):
                try:
                    dclient.images.remove(img.id, force=True)
                    removed.append(tag)
                except Exception:
                    pass
                break  # Don't try other tags for the same image
    return removed


def _preflight_validate(lab_slug: str, lab_yaml: dict, lab_dir: str = "") -> list:
    """Run fast structural checks on lab.yaml before spawning containers.

    Returns a list of dicts: {"level": "ok|warning|error", "message": str}
    """
    issues = []

    # 1. Password safety
    for cred in lab_yaml.get("credentials", []):
        password = cred.get("password", "")
        role = cred.get("role", "unknown")
        bad = [c for c in password if c in DANGEROUS_PASSWORD_CHARS]
        if bad:
            issues.append({
                "level": "error",
                "message": f"Credential '{role}' password contains dangerous char(s): "
                           f"{' '.join(repr(c) for c in bad)} -- will break through shell layers. "
                           f"Use only: # _ - @ . % ^ + ="
            })

    # 2. Command anti-patterns in test steps
    import re as _re
    for step in lab_yaml.get("test", {}).get("steps", []):
        cmd = step.get("command", "")
        name = step.get("name", "unnamed")

        if _re.search(r"-X\s+POST", cmd) and "-L" in cmd:
            issues.append({
                "level": "error",
                "message": f"Step '{name}': curl -X POST + -L causes 405 on redirects. "
                           f"Remove -X POST; -d alone implies POST."
            })

        if _re.search(r"grep\s+(-\w*P|--perl-regexp)", cmd):
            issues.append({
                "level": "warning",
                "message": f"Step '{name}': grep -P (PCRE) may not work in Alpine/BusyBox. "
                           f"Use grep -o + cut instead."
            })

        if "!=" in cmd and ("jq" in cmd or "select" in cmd):
            issues.append({
                "level": "error",
                "message": f"Step '{name}': '!=' in jq expression risks bash history expansion. "
                           f"Use select(.field) instead of select(.field != null)."
            })

    # 3. Template variable resolution check
    topo_nodes = lab_yaml.get("topology", {}).get("nodes", [])
    node_ids = {n["id"] for n in topo_nodes if n.get("id")}

    # Also check docker-compose for service names
    if lab_dir:
        compose_path = os.path.join(lab_dir, "docker-compose.yml")
        if os.path.exists(compose_path):
            try:
                with open(compose_path, "r") as f:
                    compose = yaml.safe_load(f) or {}
                for svc in compose.get("services", {}).keys():
                    node_ids.add(svc)
            except Exception:
                pass

    cred_roles = {c.get("role") for c in lab_yaml.get("credentials", []) if c.get("role")}

    for step in lab_yaml.get("test", {}).get("steps", []):
        cmd = step.get("command", "")
        name = step.get("name", "unnamed")
        import re as _re
        for m in _re.finditer(r"\{target\.([^}]+)\}", cmd):
            if m.group(1) not in node_ids:
                issues.append({
                    "level": "error",
                    "message": f"Step '{name}': {{target.{m.group(1)}}} has no matching "
                               f"topology node or compose service. Available: {sorted(node_ids) if node_ids else '(none)'}"
                })
        for m in _re.finditer(r"\{cred\.([^.}]+)\.(user|pass)\}", cmd):
            if m.group(1) not in cred_roles:
                issues.append({
                    "level": "error",
                    "message": f"Step '{name}': {{cred.{m.group(1)}.{m.group(2)}}} has no matching "
                               f"credential role. Available: {sorted(cred_roles) if cred_roles else '(none)'}"
                })

    # 4. Test steps exist check
    flag = lab_yaml.get("flag", "")
    steps = lab_yaml.get("test", {}).get("steps", [])
    if flag and not steps:
        issues.append({
            "level": "warning",
            "message": "Lab has a flag but no test: steps. The solve path cannot be validated."
        })

    return issues


# ── Main endpoint ──────────────────────────────────────────────────────────

@router.post("/exercise-test")
async def run_exercise_test(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_instructor_user),
):
    """
    Run automated exercise tester on one or more labs.

    Body:
        lab_slugs: list of lab slugs, or ["all"]
        user_id:   optional user ID to test as (default 249)
        timeout:   optional per-lab timeout in seconds (default 300)

    Returns: text/event-stream with JSON events.
    """
    lab_slugs_raw = body.get("lab_slugs", [])
    user_id = body.get("user_id") or TESTER_USER_ID
    per_lab_timeout = body.get("timeout") or DEFAULT_TIMEOUT

    # Resolve lab list (include inactive labs — tester validates before activation)
    if not lab_slugs_raw or lab_slugs_raw == ["all"]:
        query = db.query(Lab)
        labs = query.order_by(Lab.slug).all()
    else:
        query = db.query(Lab).filter(Lab.slug.in_(lab_slugs_raw))
        labs = query.all()

    # Verify test user exists
    test_user = db.query(User).filter(User.id == user_id).first()
    if not test_user:
        test_user = db.query(User).filter(User.role == "admin").first()
        if test_user:
            user_id = test_user.id

    # JWT token for real API calls (same token a student would use)
    test_user_token = create_access_token(data={"sub": test_user.username}) if test_user else ""

    admin_id = admin.id

    async def generate():
        import docker as docker_lib
        from app.database import SessionLocal

        # Use run_id from outer scope (created before generate is called).
        # Check both the in-process event (fast path, same worker) and the
        # file flag (a cancel POST may be handled by a different worker).
        def is_cancelled():
            return cancel_event.is_set() or _run_is_cancelled(run_id)

        # Background task uses its own DB session (request session is gone)
        db = SessionLocal()

        started = datetime.now(LOCAL_TZ)
        yield _ev({"type": "started", "started_at": _ts(), "total_labs": len(lab_data), "run_id": run_id})

        if not lab_data:
            yield _ev({"type": "line", "test_key": "setup", "timestamp": _ts(),
                       "level": "error", "message": "No matching labs found"})
            yield _ev({"type": "complete", "overall": "error",
                        "started_at": started.strftime("%H:%M:%S"),
                        "completed_at": _ts(),
                        "duration_seconds": 0, "summary": {}})
            db.close()
            return

        overall_results: Dict[str, str] = {}  # slug → status

        # ── Section accumulator for DB persistence ──
        # Tracks sections per lab so we can save full results after each lab_end.
        _lab_sections: Dict[str, list] = {}   # slug → [section dicts]
        _section_buf: Dict[str, dict] = {}    # test_key → current section dict

        def _track_section_start(test_key: str, name: str, lab_slug: str):
            sec = {"name": name, "test_key": test_key, "status": "running", "lines": []}
            _section_buf[test_key] = sec
            _lab_sections.setdefault(lab_slug, []).append(sec)

        def _track_line(test_key: str, timestamp: str, level: str, message: str):
            sec = _section_buf.get(test_key)
            if sec:
                sec["lines"].append({"timestamp": timestamp, "level": level, "message": message})

        def _track_section_end(test_key: str, status: str):
            sec = _section_buf.get(test_key)
            if sec:
                sec["status"] = status

        def _persist_lab_result(lab_obj, lab_slug: str, status: str, duration: float,
                                admin_user_id: int, current_run_id: str):
            """Upsert ExerciseTestResult for this lab (latest replaces older)."""
            try:
                from app.database import SessionLocal
                persist_db = SessionLocal()
                try:
                    existing = persist_db.query(ExerciseTestResult).filter(
                        ExerciseTestResult.lab_slug == lab_slug
                    ).first()
                    sections_data = _lab_sections.get(lab_slug, [])
                    now = datetime.now(LOCAL_TZ)
                    track = lab_slug.split("-")[0] if "-" in lab_slug else ""

                    if existing:
                        existing.lab_name = lab_obj["name"]
                        existing.track = track
                        existing.category = lab_obj["category"]
                        existing.status = status
                        existing.duration_seconds = round(duration, 1)
                        existing.tested_at = now
                        existing.tested_by_id = admin_user_id
                        existing.run_id = current_run_id
                        existing.sections_json = json.dumps(sections_data, default=str)
                    else:
                        new_result = ExerciseTestResult(
                            lab_slug=lab_slug,
                            lab_name=lab_obj["name"],
                            track=track,
                            category=lab_obj["category"],
                            status=status,
                            duration_seconds=round(duration, 1),
                            tested_at=now,
                            tested_by_id=admin_user_id,
                            run_id=current_run_id,
                            sections_json=json.dumps(sections_data, default=str),
                        )
                        persist_db.add(new_result)
                    persist_db.commit()
                finally:
                    persist_db.close()
            except Exception as exc:
                logger.warning("Failed to persist exercise test result for %s: %s", lab_slug, exc)

        def _emit(data: dict) -> str:
            """Yield-helper: emits SSE AND tracks section data for persistence."""
            etype = data.get("type")
            tk = data.get("test_key", "")
            lab_slug_from_key = tk.rsplit("_", 1)[0] if "_" in tk else ""
            if etype == "section_start":
                _track_section_start(tk, data.get("name", ""), lab_slug_from_key)
            elif etype == "line":
                _track_line(tk, data.get("timestamp", ""), data.get("level", ""), data.get("message", ""))
            elif etype == "section_end":
                _track_section_end(tk, data.get("status", ""))
            return _ev(data)

        for lab_idx, lab in enumerate(lab_data):
            if is_cancelled():
                yield _emit({"type": "line", "test_key": "setup", "timestamp": _ts(),
                            "level": "warning", "message": "Test cancelled by user"})
                break

            # SSE heartbeat between labs to keep connection alive during long runs
            if lab_idx > 0:
                yield SSE_HEARTBEAT

            lab_start = time.monotonic()
            lab_status = "ok"
            slug = lab["slug"]

            yield _ev({"type": "lab_start", "lab_slug": slug, "lab_name": lab["name"],
                        "lab_index": lab_idx + 1, "total_labs": len(lab_data)})

            # Load YAML topology
            lab_yaml = _load_lab_yaml(slug)
            topo_nodes = [n for n in lab_yaml.get("topology", {}).get("nodes", [])
                          if n.get("ip_offset")]
            hostnames = lab_yaml.get("hostnames", [])
            credentials = lab_yaml.get("credentials", [])
            test_steps = lab_yaml.get("test", {}).get("steps", [])
            flag_plaintext = lab_yaml.get("flag", "")

            second_octet, third_octet = get_subnet_id(user_id, slug)
            subnet = f"10.{second_octet}.{third_octet}.0/24"
            project_name = f"lab_{user_id}_{slug}"
            tester_name = f"ocr-tester-{user_id}-{slug}"
            network_name = project_name

            # Build node_id → IP map
            node_ip_map: Dict[str, str] = {}
            for node in topo_nodes:
                node_ip_map[node["id"]] = f"10.{second_octet}.{third_octet}.{node['ip_offset']}"
            # Also map by hostnames
            for h in hostnames:
                ip = f"10.{second_octet}.{third_octet}.{h['ip_offset']}"
                # Find matching node_id if any
                for node in topo_nodes:
                    if node.get("ip_offset") == h["ip_offset"] and node["id"] not in node_ip_map:
                        node_ip_map[node["id"]] = ip

            # ── Fallback: discover hosts from docker-compose.yml ─────
            if not node_ip_map:
                compose_yaml = _load_compose_yaml(slug)
                for svc_name, svc_def in compose_yaml.get("services", {}).items():
                    labels = svc_def.get("labels", {})
                    # labels can be a dict or a list of "key=value" strings
                    if isinstance(labels, list):
                        label_dict = {}
                        for item in labels:
                            if "=" in item:
                                k, v = item.split("=", 1)
                                label_dict[k.strip()] = v.strip()
                        labels = label_dict
                    offset = labels.get("ip_offset")
                    if offset:
                        ip = f"10.{second_octet}.{third_octet}.{offset}"
                        node_ip_map[svc_name] = ip

            # ── Guard: skip if another user has an active session ─────
            active_other = db.query(LabSession).filter(
                LabSession.lab_id == lab["id"],
                LabSession.user_id != user_id,
                LabSession.status.in_(["starting", "running"]),
            ).first()
            if active_other:
                other_name = active_other.user.username if active_other.user else f"user #{active_other.user_id}"
                yield _emit({"type": "section_start", "name": f"Spawn: {lab['name']}", "test_key": f"{slug}_spawn"})
                yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                            "level": "warn", "message": f"SKIPPED — {other_name} has an active session (#{active_other.id}). Will not destroy student work."})
                yield _emit({"type": "section_end", "test_key": f"{slug}_spawn", "passed": False})
                overall_results[slug] = "skipped"
                yield _ev({"type": "lab_end", "lab_slug": slug, "status": "skipped", "duration_seconds": 0})
                continue

            # ── Guard: skip labs with no compose file and no test steps ─────
            compose_yaml = _load_compose_yaml(slug)
            if not compose_yaml.get("services") and not test_steps:
                yield _emit({"type": "section_start", "name": f"Spawn: {lab['name']}", "test_key": f"{slug}_spawn"})
                yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                            "level": "warn", "message": "SKIPPED — no containers and no test steps (interactive lab)"})
                yield _emit({"type": "section_end", "test_key": f"{slug}_spawn", "status": "skipped"})
                overall_results[slug] = "skipped"
                yield _ev({"type": "lab_end", "lab_slug": slug, "status": "skipped", "duration_seconds": 0})
                continue

            # ── Pre-flight validation (fast, before containers) ─────
            track_slug_pf = slug.split("-")[0].lower()
            track_dir_pf = get_track_directory_name(track_slug_pf)
            lab_dir_pf = f"/labs/{track_dir_pf}/{slug}"
            preflight_issues = _preflight_validate(slug, lab_yaml, lab_dir_pf)
            preflight_errors = [i for i in preflight_issues if i["level"] == "error"]

            if preflight_issues:
                yield _emit({"type": "section_start", "name": "Pre-flight Validation", "test_key": f"{slug}_preflight"})
                for issue in preflight_issues:
                    yield _emit({"type": "line", "test_key": f"{slug}_preflight", "timestamp": _ts(),
                                "level": issue["level"], "message": issue["message"]})
                pf_status = "error" if preflight_errors else "warning"
                yield _emit({"type": "section_end", "test_key": f"{slug}_preflight", "status": pf_status})
                if preflight_errors:
                    lab_status = "error"
                    yield _emit({"type": "line", "test_key": f"{slug}_preflight", "timestamp": _ts(),
                                "level": "error", "message": f"BLOCKED: {len(preflight_errors)} pre-flight error(s) — fix before testing"})
                    overall_results[slug] = lab_status
                    elapsed = time.monotonic() - lab_start
                    yield _ev({"type": "lab_end", "lab_slug": slug, "status": lab_status,
                                "duration_seconds": round(elapsed, 1)})
                    _persist_lab_result(lab, slug, lab_status, elapsed, admin_id, run_id)
                    continue

            sim_session = None
            tester_container = None
            dclient = None
            extracted_flag = ""
            flag_submitted_via_api = False

            try:
                dclient = docker_lib.from_env()

                # ── Stale image cleanup (ensures Dockerfile changes take effect) ──
                removed_images = await _run_blocking(_cleanup_stale_images, slug, user_id)
                if removed_images:
                    yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                                "level": "info", "message": f"Cleared {len(removed_images)} cached image(s): {', '.join(removed_images[:5])}"})

                # ── Step 1: Spawn lab ──────────────────────────────────────
                yield _emit({"type": "section_start", "name": f"Spawn: {lab['name']}", "test_key": f"{slug}_spawn"})

                # Kill any existing session for this user first
                existing = db.query(LabSession).filter(
                    LabSession.user_id == user_id,
                    LabSession.status.in_(["starting", "running"]),
                ).first()
                if existing:
                    try:
                        await _run_blocking(docker_manager.destroy_lab_environment, user_id, existing.lab.slug)
                        existing.status = "stopped"
                        existing.stopped_at = datetime.now(timezone.utc)
                        db.commit()
                        yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                                    "level": "info", "message": f"Cleaned up previous session #{existing.id}"})
                    except Exception:
                        pass

                session_record = LabSession(
                    user_id=user_id, lab_id=lab["id"], status="starting",
                    is_diagnostic=True,
                    started_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
                db.add(session_record)
                db.commit()
                db.refresh(session_record)

                result = await _run_blocking(
                    docker_manager.create_lab_environment,
                    user_id=user_id, lab_slug=slug,
                    compose_content=lab["compose_file"],
                )
                session_record.status = "running"
                session_record.network_id = result.get("network_id", network_name)
                session_record.network_subnet = result.get("subnet", subnet)
                db.commit()
                sim_session = session_record

                yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                            "level": "ok", "message": f"Lab spawned (session #{sim_session.id}, subnet {subnet})"})
                yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                            "level": "info", "message": f"Waiting {CONTAINER_INIT_WAIT}s for containers..."})
                await asyncio.sleep(CONTAINER_INIT_WAIT)
                yield _emit({"type": "section_end", "test_key": f"{slug}_spawn", "status": "ok"})

                # ── Step 2: Attach tester sidecar ──────────────────────────
                yield _emit({"type": "section_start", "name": "Attach Test Tools (nmap, curl, ssh...)", "test_key": f"{slug}_sidecar"})
                try:
                    # Remove stale tester container if exists
                    try:
                        old = dclient.containers.get(tester_name)
                        await _run_blocking(old.remove, force=True)
                    except Exception:
                        pass

                    tester_container = await _run_blocking(
                        dclient.containers.run,
                        TESTER_IMAGE,
                        name=tester_name,
                        network=network_name,
                        detach=True,
                        labels={"com.docker.compose.project": project_name, "role": "tester"},
                        mem_limit="128m",
                        cpu_period=100000, cpu_quota=50000,
                    )
                    await asyncio.sleep(SIDECAR_INIT_WAIT)
                    yield _emit({"type": "line", "test_key": f"{slug}_sidecar", "timestamp": _ts(),
                                "level": "ok", "message": f"Test tools connected to lab network ({network_name})"})
                    yield _emit({"type": "section_end", "test_key": f"{slug}_sidecar", "status": "ok"})
                except Exception as e:
                    yield _emit({"type": "line", "test_key": f"{slug}_sidecar", "timestamp": _ts(),
                                "level": "error", "message": f"Failed to attach test tools: {e}"})
                    yield _emit({"type": "section_end", "test_key": f"{slug}_sidecar", "status": "error"})
                    lab_status = "error"

                # ── Step 2b: Install extra test tools if declared ─────────
                extra_tools = lab_yaml.get("test", {}).get("tools", [])
                if extra_tools and tester_container and lab_status != "error":
                    pkgs = " ".join(extra_tools)
                    install_cmd = f"apk add --no-cache {pkgs}"
                    r = await _exec_in_tester(tester_container, install_cmd, 60)
                    if r.exit_code == 0:
                        yield _emit({"type": "line", "test_key": f"{slug}_sidecar", "timestamp": _ts(),
                                    "level": "info", "message": f"Installed extra tools: {pkgs}"})
                    else:
                        yield _emit({"type": "line", "test_key": f"{slug}_sidecar", "timestamp": _ts(),
                                    "level": "warning", "message": f"Failed to install extra tools ({pkgs}): {r.stderr[:200]}"})

                # ── Step 3: Container health ───────────────────────────────
                if tester_container and lab_status != "error":
                    yield _emit({"type": "section_start", "name": "Container Health", "test_key": f"{slug}_health"})
                    health_status = "ok"
                    containers = await _run_blocking(
                        dclient.containers.list,
                        filters={"label": f"com.docker.compose.project={project_name}"},
                    )
                    lab_containers = [c for c in containers if c.name != tester_name]
                    if not lab_containers:
                        yield _emit({"type": "line", "test_key": f"{slug}_health", "timestamp": _ts(),
                                    "level": "error", "message": "No lab containers found"})
                        health_status = "error"
                        lab_status = "error"
                    else:
                        for c in lab_containers:
                            short = c.name.replace(f"{project_name}-", "").replace(f"{project_name}_", "")
                            status = c.status
                            level = "ok" if status == "running" else "error"
                            yield _emit({"type": "line", "test_key": f"{slug}_health", "timestamp": _ts(),
                                        "level": level, "message": f"{short}: {status}"})
                            if level == "error":
                                health_status = "error"
                                lab_status = "error"
                    yield _emit({"type": "section_end", "test_key": f"{slug}_health", "status": health_status})

                # ── Step 4: Ping ───────────────────────────────────────────
                if is_cancelled():
                    lab_status = "cancelled"
                    raise Exception("Cancelled")
                if tester_container and lab_status != "error":
                    yield _emit({"type": "section_start", "name": "Network Connectivity", "test_key": f"{slug}_ping"})
                    ping_status = "ok"
                    targets = list(node_ip_map.items())
                    if not targets:
                        # Fall back to hostnames
                        for h in hostnames:
                            ip = f"10.{second_octet}.{third_octet}.{h['ip_offset']}"
                            targets.append((h.get("hostname", h["ip_offset"]), ip))

                    for label, ip in targets:
                        r = await _exec_in_tester(tester_container, f"ping -c 2 -W 2 {ip}", 10
                        )
                        if r.exit_code == 0:
                            yield _emit({"type": "line", "test_key": f"{slug}_ping", "timestamp": _ts(),
                                        "level": "ok", "message": f"{label} ({ip}): reachable"})
                        else:
                            yield _emit({"type": "line", "test_key": f"{slug}_ping", "timestamp": _ts(),
                                        "level": "error", "message": f"{label} ({ip}): unreachable"})
                            ping_status = "error"
                    yield _emit({"type": "section_end", "test_key": f"{slug}_ping", "status": ping_status})

                # Track discovered ports for service verification
                discovered_ports: Dict[str, List[dict]] = {}

                # ── Step 5: Port scan ──────────────────────────────────────
                if is_cancelled():
                    lab_status = "cancelled"
                    raise Exception("Cancelled")
                if tester_container and lab_status != "error" and node_ip_map:
                    yield _emit({"type": "section_start", "name": "Port Scan", "test_key": f"{slug}_ports"})
                    port_status = "ok"

                    for node_id, ip in node_ip_map.items():
                        # Get declared ports from topology if available
                        # Ports can be int (TCP) or string like "161/udp"
                        raw_ports = []
                        for node in topo_nodes:
                            if node["id"] == node_id:
                                raw_ports = node.get("ports", [])
                                break

                        tcp_ports = []
                        udp_ports = []
                        for p in raw_ports:
                            ps = str(p)
                            if ps.endswith("/udp"):
                                udp_ports.append(int(ps.replace("/udp", "")))
                            else:
                                tcp_ports.append(int(ps.replace("/tcp", "")))

                        # Scan: use declared ports if known, otherwise discover
                        # Note: -sV omitted here — version probes hang on
                        # Flask/Werkzeug and other dev servers.  Service
                        # verification is done separately below.
                        port_list = []

                        # TCP scan
                        if tcp_ports:
                            port_str = ",".join(str(p) for p in tcp_ports)
                            nmap_cmd = f"nmap -Pn -n -p {port_str} {ip}"
                        elif not tcp_ports and not udp_ports:
                            nmap_cmd = f"nmap -Pn -n --top-ports 200 {ip}"
                        else:
                            nmap_cmd = None  # UDP-only node, skip TCP scan

                        if nmap_cmd:
                            yield _emit({"type": "line", "test_key": f"{slug}_ports", "timestamp": _ts(),
                                        "level": "info", "message": f"$ {nmap_cmd}"})
                            r = await _exec_in_tester(tester_container, nmap_cmd, 60)

                            # Parse nmap TCP output for open ports
                            for match in re.finditer(r"(\d+)/tcp\s+open\s+(\S+)((?:[^\S\n]+(?!\d+/tcp)\S+)*)", r.stdout):
                                port_num = int(match.group(1))
                                service = match.group(2)
                                version = match.group(3).strip()
                                port_list.append({"port": port_num, "service": service, "version": version, "proto": "tcp"})
                                yield _emit({"type": "line", "test_key": f"{slug}_ports", "timestamp": _ts(),
                                            "level": "ok", "message": f"  {port_num}/tcp open  {service}  {version}"})

                        # UDP scan (if any UDP ports declared)
                        if udp_ports:
                            udp_str = ",".join(str(p) for p in udp_ports)
                            udp_cmd = f"nmap -Pn -n -sU -p {udp_str} {ip}"
                            yield _emit({"type": "line", "test_key": f"{slug}_ports", "timestamp": _ts(),
                                        "level": "info", "message": f"$ {udp_cmd}"})
                            r = await _exec_in_tester(tester_container, udp_cmd, 60)
                            for match in re.finditer(r"(\d+)/udp\s+open\s+(\S+)((?:[^\S\n]+(?!\d+/udp)\S+)*)", r.stdout):
                                port_num = int(match.group(1))
                                service = match.group(2)
                                version = match.group(3).strip()
                                port_list.append({"port": port_num, "service": service, "version": version, "proto": "udp"})
                                yield _emit({"type": "line", "test_key": f"{slug}_ports", "timestamp": _ts(),
                                            "level": "ok", "message": f"  {port_num}/udp open  {service}  {version}"})

                        discovered_ports[node_id] = port_list

                        if not port_list:
                            yield _emit({"type": "line", "test_key": f"{slug}_ports", "timestamp": _ts(),
                                        "level": "warning", "message": f"  No open ports found on {node_id} ({ip})"})
                            port_status = "warning" if port_status == "ok" else port_status

                        # Verify declared ports are among discovered
                        all_declared = tcp_ports + udp_ports
                        if all_declared:
                            found_ports = {p["port"] for p in port_list}
                            for dp in all_declared:
                                if dp not in found_ports:
                                    yield _emit({"type": "line", "test_key": f"{slug}_ports", "timestamp": _ts(),
                                                "level": "error", "message": f"  Expected port {dp} not open on {node_id}"})
                                    port_status = "error"
                                    lab_status = "error"

                    yield _emit({"type": "section_end", "test_key": f"{slug}_ports", "status": port_status})

                # ── Step 6: Service banners ────────────────────────────────
                if is_cancelled():
                    lab_status = "cancelled"
                    raise Exception("Cancelled")
                if tester_container and lab_status != "error" and discovered_ports:
                    yield _emit({"type": "section_start", "name": "Service Verification", "test_key": f"{slug}_services"})
                    svc_status = "ok"

                    for node_id, ports in discovered_ports.items():
                        ip = node_ip_map.get(node_id, "")
                        if not ip or not ports:
                            continue

                        for p in ports:
                            port = p["port"]
                            service = p["service"]

                            # HTTP services
                            if service in ("http", "http-proxy") or port in (80, 8080, 8443):
                                r = await _exec_in_tester(tester_container,
                                    f"curl -sk -o /dev/null -w '%{{http_code}}' http://{ip}:{port}/", 10
                                )
                                code = r.stdout.strip()
                                level = "ok" if code and code[0] in ("2", "3") else "warning"
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} HTTP:{port} → {code}"})
                                if level != "ok":
                                    svc_status = "warning" if svc_status == "ok" else svc_status

                            # HTTPS services
                            elif service == "ssl/http" or port == 443:
                                r = await _exec_in_tester(tester_container,
                                    f"curl -sk -o /dev/null -w '%{{http_code}}' https://{ip}:{port}/", 10
                                )
                                code = r.stdout.strip()
                                level = "ok" if code and code[0] in ("2", "3") else "warning"
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} HTTPS:{port} → {code}"})
                                if level != "ok":
                                    svc_status = "warning" if svc_status == "ok" else svc_status

                            # SSH services
                            elif service == "ssh" or port == 22:
                                r = await _exec_in_tester(tester_container,
                                    f"echo '' | nc -w 3 {ip} {port} 2>&1 | head -1", 5
                                )
                                banner = r.stdout.strip()[:80]
                                level = "ok" if "SSH" in banner.upper() else "warning"
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} SSH:{port} → {banner or '(no banner)'}"})
                                if level != "ok":
                                    svc_status = "warning" if svc_status == "ok" else svc_status

                            # FTP services
                            elif service == "ftp" or port == 21:
                                r = await _exec_in_tester(tester_container,
                                    f"echo '' | nc -w 3 {ip} {port} 2>&1 | head -1", 5
                                )
                                banner = r.stdout.strip()[:80]
                                level = "ok" if "220" in banner else "warning"
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} FTP:{port} → {banner or '(no banner)'}"})
                                if level != "ok":
                                    svc_status = "warning" if svc_status == "ok" else svc_status

                            # SMB services
                            elif service in ("microsoft-ds", "netbios-ssn") or port in (445, 139):
                                r = await _exec_in_tester(tester_container,
                                    f"smbclient -L //{ip} -N 2>&1 | head -20", 10
                                )
                                output = r.stdout.strip()
                                # Check for share listing or server string
                                has_shares = "Sharename" in output or "Server" in output
                                level = "ok" if has_shares else "warning"
                                # Show first few lines of output
                                for line in output.splitlines()[:8]:
                                    yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                                "level": "info", "message": f"  {line}"})
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} SMB:{port} → {'shares listed' if has_shares else 'no share listing'}"})
                                if level != "ok":
                                    svc_status = "warning" if svc_status == "ok" else svc_status

                            # SMTP services
                            elif service == "smtp" or port == 25:
                                r = await _exec_in_tester(tester_container,
                                    f"echo '' | nc -w 3 {ip} {port} 2>&1 | head -1", 5
                                )
                                banner = r.stdout.strip()[:80]
                                level = "ok" if "220" in banner or "SMTP" in banner.upper() else "warning"
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} SMTP:{port} → {banner or '(no banner)'}"})
                                if level != "ok":
                                    svc_status = "warning" if svc_status == "ok" else svc_status

                            # RDP services
                            elif service in ("ms-wbt-server",) or port == 3389:
                                r = await _exec_in_tester(tester_container,
                                    f"echo '' | nc -w 3 {ip} {port} 2>&1 | head -1", 5
                                )
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": "ok", "message": f"{node_id} RDP:{port} → accepting connections"})

                            # MySQL/MariaDB
                            elif service == "mysql" or port == 3306:
                                r = await _exec_in_tester(tester_container,
                                    f"echo '' | nc -w 3 {ip} {port} 2>&1 | head -1", 5
                                )
                                banner = r.stdout.strip()[:80]
                                level = "ok" if banner else "warning"
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": level, "message": f"{node_id} MySQL:{port} → {banner or '(no banner)'}"})

                            # Generic TCP check
                            else:
                                r = await _exec_in_tester(tester_container,
                                    f"echo '' | nc -w 3 {ip} {port} 2>&1 | head -1", 5
                                )
                                banner = r.stdout.strip()[:80]
                                yield _emit({"type": "line", "test_key": f"{slug}_services", "timestamp": _ts(),
                                            "level": "info", "message": f"{node_id} TCP:{port} → {banner or '(connected)'}"})

                    yield _emit({"type": "section_end", "test_key": f"{slug}_services", "status": svc_status})

                # ── Step 7: Flag Retrieval (probe services for flag) ──────
                if is_cancelled():
                    lab_status = "cancelled"
                    raise Exception("Cancelled")
                if tester_container and discovered_ports:
                    yield _emit({"type": "section_start", "name": "Flag Retrieval", "test_key": f"{slug}_flagret"})
                    flag_ret_status = "ok"
                    all_output = ""

                    for node_id, ports_info in discovered_ports.items():
                        ip = node_ip_map.get(node_id, "")
                        if not ip:
                            continue
                        port_nums = [p["port"] for p in ports_info]
                        services = {p["port"]: p["service"] for p in ports_info}

                        # ── SMB (445 / 139) ──────────────────────────────
                        if 445 in port_nums or 139 in port_nums:
                            smb_port = 445 if 445 in port_nums else 139
                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                        "level": "info", "message": f"{node_id} → probing SMB shares on {ip}:{smb_port}"})
                            # List shares
                            r = await _exec_in_tester(tester_container,
                                f"smbclient -L //{ip} -N --no-pass 2>/dev/null", 15
                            )
                            shares = []
                            for m in re.finditer(r"^\s+(\S+)\s+Disk", r.stdout, re.MULTILINE):
                                share_name = m.group(1)
                                if share_name.lower() not in ("ipc$", "print$"):
                                    shares.append(share_name)
                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                        "level": "info", "message": f"  Disk shares found: {shares if shares else '(none)'}"})

                            for share in shares:
                                # List files in the share
                                r = await _exec_in_tester(tester_container,
                                    f"smbclient //{ip}/{share} -N --no-pass -c 'recurse; ls' 2>/dev/null", 15
                                )
                                all_output += r.stdout + "\n"
                                # Look for likely flag files
                                flag_files = []
                                for line in r.stdout.splitlines():
                                    fname = line.strip().split()[0] if line.strip() else ""
                                    if fname and any(kw in fname.lower() for kw in
                                                     ("flag", "secret", "key", "credentials", "password", "backup", "config")):
                                        flag_files.append(fname)
                                if not flag_files:
                                    # Try common names anyway
                                    flag_files = ["flag.txt", "secret.txt"]

                                for fname in flag_files:
                                    r2 = await _exec_in_tester(tester_container,
                                        f"smbclient //{ip}/{share} -N --no-pass -c 'get {fname} /dev/stdout' 2>/dev/null", 10
                                    )
                                    content = r2.stdout.strip()
                                    if content:
                                        all_output += content + "\n"
                                        yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                                    "level": "info", "message": f"  SMB //{share}/{fname}: {content[:120]}"})
                                        fm = re.search(r"OCR\{[^}]+\}", content)
                                        if fm and not extracted_flag:
                                            extracted_flag = fm.group()
                                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                                        "level": "ok", "message": f"  FLAG FOUND via SMB: {extracted_flag}"})

                        # ── HTTP (80 / 8080 / 8443 / 443) ────────────────
                        http_ports = [p for p in port_nums if p in (80, 8080, 8443, 443, 8000, 8888)
                                      or services.get(p, "") in ("http", "http-proxy", "https")]
                        for hp in http_ports:
                            if extracted_flag:
                                break
                            scheme = "https" if hp in (443, 8443) else "http"
                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                        "level": "info", "message": f"{node_id} → probing {scheme}://{ip}:{hp}"})
                            # Try common flag paths
                            for path in ["/flag.txt", "/flag", "/secret.txt", "/", "/index.html",
                                         "/robots.txt", "/config", "/admin"]:
                                r = await _exec_in_tester(tester_container,
                                    f"curl -sk --max-time 5 {scheme}://{ip}:{hp}{path} 2>/dev/null", 8
                                )
                                content = r.stdout.strip()
                                if content:
                                    all_output += content + "\n"
                                    fm = re.search(r"OCR\{[^}]+\}", content)
                                    if fm and not extracted_flag:
                                        extracted_flag = fm.group()
                                        yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                                    "level": "ok", "message": f"  FLAG FOUND via HTTP {path}: {extracted_flag}"})
                                        break
                            else:
                                yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                            "level": "info", "message": f"  No flag in HTTP responses from {ip}:{hp}"})

                        # ── FTP (21) ──────────────────────────────────────
                        if 21 in port_nums and not extracted_flag:
                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                        "level": "info", "message": f"{node_id} → probing FTP on {ip}:21"})
                            # Try anonymous listing
                            r = await _exec_in_tester(tester_container,
                                f"curl -s --max-time 10 ftp://anonymous:@{ip}/ 2>/dev/null", 15
                            )
                            all_output += r.stdout + "\n"
                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                        "level": "info", "message": f"  FTP listing: {r.stdout.strip()[:200] if r.stdout.strip() else '(empty/denied)'}"})
                            # Try common flag files
                            for fname in ["flag.txt", "secret.txt", "config-backups/flag.txt",
                                          "config-backups/firewall.conf.bak", "public/flag.txt"]:
                                r2 = await _exec_in_tester(tester_container,
                                    f"curl -s --max-time 8 ftp://anonymous:@{ip}/{fname} 2>/dev/null", 12
                                )
                                content = r2.stdout.strip()
                                if content and "550" not in content[:10]:
                                    all_output += content + "\n"
                                    yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                                "level": "info", "message": f"  FTP /{fname}: {content[:120]}"})
                                    fm = re.search(r"OCR\{[^}]+\}", content)
                                    if fm and not extracted_flag:
                                        extracted_flag = fm.group()
                                        yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                                    "level": "ok", "message": f"  FLAG FOUND via FTP: {extracted_flag}"})
                                        break

                    # Also scan all accumulated output once more for a flag
                    if not extracted_flag and all_output:
                        fm = re.search(r"OCR\{[^}]+\}", all_output)
                        if fm:
                            extracted_flag = fm.group()
                            yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                        "level": "ok", "message": f"FLAG FOUND in output: {extracted_flag}"})

                    if extracted_flag:
                        yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                    "level": "ok", "message": f"Extracted flag: {extracted_flag}"})
                    else:
                        yield _emit({"type": "line", "test_key": f"{slug}_flagret", "timestamp": _ts(),
                                    "level": "info", "message": "No flag found via auto-retrieval (may require test: steps)"})
                        flag_ret_status = "warning" if lab["flag_hash"] else "ok"

                    yield _emit({"type": "section_end", "test_key": f"{slug}_flagret", "status": flag_ret_status})

                # ── Step 8: Custom solve steps (from lab.yaml test:) ───────
                if tester_container and test_steps:
                    yield _emit({"type": "section_start", "name": "Solve Steps", "test_key": f"{slug}_solve"})
                    solve_status = "ok"
                    last_output = ""
                    for step_idx, step in enumerate(test_steps):
                        step_name = step.get("name", "unnamed")
                        step_raw = step["command"]
                        step_cmd = _resolve_template(
                            step_raw, node_ip_map, subnet, credentials
                        )
                        step_timeout = step.get("timeout", EXEC_TIMEOUT)
                        expect = step.get("expect", "")

                        yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                    "level": "info", "message": f"$ {step_cmd}"})
                        r = await _exec_in_tester(tester_container, step_cmd, step_timeout
                        )
                        last_output = r.stdout
                        # Show first few lines of output
                        for line in r.stdout.strip().splitlines()[:10]:
                            yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                        "level": "info", "message": f"  {line}"})
                        if len(r.stdout.strip().splitlines()) > 10:
                            yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                        "level": "info", "message": f"  ... ({len(r.stdout.strip().splitlines())} lines total)"})

                        # Try to extract flag from solve step output
                        if not extracted_flag:
                            fm = re.search(r"OCR\{[^}]+\}", r.stdout)
                            if fm:
                                extracted_flag = fm.group()
                                yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                            "level": "ok", "message": f"  FLAG FOUND in solve output: {extracted_flag}"})

                        step_passed = True
                        if expect:
                            if expect in r.stdout:
                                yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                            "level": "ok", "message": f"[PASS] {step_name}: found expected output"})
                            else:
                                yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                            "level": "error", "message": f"[FAIL] {step_name}: expected '{expect}' not found"})
                                step_passed = False
                                solve_status = "error"
                                lab_status = "error"
                        else:
                            level = "ok" if r.exit_code == 0 else "error"
                            yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                        "level": level, "message": f"[{'PASS' if level == 'ok' else 'FAIL'}] {step_name}: exit code {r.exit_code}"})
                            if level == "error":
                                step_passed = False
                                solve_status = "error"
                                lab_status = "error"

                        # ── Enhanced diagnostics on failure ──────────────
                        if not step_passed:
                            # Show stderr if available
                            stderr_text = r.stderr.strip() if r.stderr else ""
                            if stderr_text:
                                for sline in stderr_text.splitlines()[:5]:
                                    yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                                "level": "error", "message": f"  STDERR: {sline}"})

                                # Check for known error patterns and provide hints
                                for pattern, hint in ERROR_PATTERN_HINTS.items():
                                    if pattern in stderr_text or pattern in r.stdout:
                                        yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                                    "level": "warning", "message": f"  HINT: {hint}"})
                                        break

                            # Show template vs resolved command if different
                            if step_raw != step_cmd:
                                yield _emit({"type": "line", "test_key": f"{slug}_solve", "timestamp": _ts(),
                                            "level": "info", "message": f"  Template: {step_raw}"})

                    yield _emit({"type": "section_end", "test_key": f"{slug}_solve", "status": solve_status})

                # ── Step 9: Flag Validation + Real API Submission ─────────
                flag_submitted_via_api = False
                if tester_container and lab["flag_hash"]:
                    yield _emit({"type": "section_start", "name": "Flag Validation", "test_key": f"{slug}_flag"})
                    flag_status = "ok"

                    # Reference check: does lab.yaml flag match the DB hash?
                    if flag_plaintext:
                        yaml_hash = hashlib.sha256(flag_plaintext.encode()).hexdigest()
                        yaml_match = hmac.compare_digest(yaml_hash, lab["flag_hash"])
                        if yaml_match:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "ok", "message": "lab.yaml flag matches DB hash (reference check)"})
                        else:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "error", "message": "lab.yaml flag does NOT match DB hash -- flag_hash in DB may be stale"})
                            flag_status = "error"
                            lab_status = "error"

                    # The real test: only submit flags extracted from the live environment
                    if extracted_flag:
                        yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                    "level": "info", "message": f"Extracted flag: {extracted_flag}"})

                        # Pre-check: hash verify before hitting the API
                        submitted_hash = hashlib.sha256(extracted_flag.encode()).hexdigest()
                        hash_match = hmac.compare_digest(submitted_hash, lab["flag_hash"])

                        if hash_match:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "ok", "message": "Hash pre-check: CORRECT"})
                        else:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "error", "message": f"Hash pre-check: MISMATCH -- '{extracted_flag}' wrong"})
                            flag_status = "error"
                            lab_status = "error"

                        # Clear prior completions so "already_completed" doesn't block the API
                        try:
                            prior = db.query(LabCompletion).filter(
                                LabCompletion.user_id == user_id,
                                LabCompletion.lab_id == lab["id"],
                            ).all()
                            for pc in prior:
                                db.delete(pc)
                            if prior:
                                db.commit()
                                yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                            "level": "info", "message": f"Cleared {len(prior)} prior completion(s)"})
                        except Exception:
                            pass

                        # ── REAL API CALL ── same endpoint a student hits ──
                        yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                    "level": "info", "message": f"POST /api/exercises/labs/{lab['id']}/submit-flag (real API)"})
                        api_result = await asyncio.to_thread(
                            _call_submit_flag_api, lab["id"], extracted_flag, test_user_token
                        )
                        status_code = api_result["status_code"]
                        body = api_result["body"]
                        yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                    "level": "info", "message": f"  Response: {status_code} {json.dumps(body)[:200]}"})

                        if status_code == 200:
                            if body.get("correct"):
                                flag_submitted_via_api = True
                                yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                            "level": "ok", "message": "API accepted flag -- full pipeline VERIFIED"})
                                yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                            "level": "ok", "message": "  (auth + rate-limit + hash + FlagAttempt + LabCompletion + activity log)"})
                                if body.get("already_completed"):
                                    yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                                "level": "info", "message": "  Note: API said 'already_completed' (prior completion existed)"})
                            else:
                                yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                            "level": "error", "message": f"API REJECTED flag: {body.get('message', '?')}"})
                                flag_status = "error"
                                lab_status = "error"
                        elif status_code == 429:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "warning", "message": "API rate-limited (429) -- too many recent attempts"})
                            flag_status = "warning"
                        elif status_code == 401:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "error", "message": "API auth failed (401) -- test user token invalid"})
                            flag_status = "error"
                            lab_status = "error"
                        else:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "error", "message": f"API error ({status_code}): {body}"})
                            flag_status = "error"
                            lab_status = "error"
                    else:
                        # No flag was extracted from the live environment.
                        # This is a FAILURE: if the tester can't extract the flag,
                        # a student can't either — the exercise is unsolvable as designed.
                        has_steps = bool(test_steps)
                        yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                    "level": "error",
                                    "message": "FAIL: Flag not found in live environment -- student cannot retrieve it organically"})
                        if has_steps:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "error",
                                        "message": "test: steps ran but did not output the flag -- last step must echo the full OCR{...} string"})
                        else:
                            yield _emit({"type": "line", "test_key": f"{slug}_flag", "timestamp": _ts(),
                                        "level": "error",
                                        "message": "No test: steps defined -- add steps to lab.yaml that extract and output the flag"})
                        flag_status = "error"
                        lab_status = "error"

                    yield _emit({"type": "section_end", "test_key": f"{slug}_flag", "status": flag_status})

            except Exception as e:
                if is_cancelled():
                    lab_status = "cancelled"
                    try:
                        yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                                    "level": "warning", "message": "Test cancelled by user"})
                    except Exception:
                        pass
                else:
                    lab_status = "error"
                    try:
                        yield _emit({"type": "line", "test_key": f"{slug}_spawn", "timestamp": _ts(),
                                    "level": "error", "message": f"Unexpected error: {e}"})
                    except Exception:
                        pass

            finally:
                # ── Step 10: Cleanup ──────────────────────────────────────
                # IMPORTANT: Docker cleanup must run even if the SSE stream
                # is disconnected (e.g. user hit Cancel and frontend aborted
                # the fetch).  Wrap yields in try/except so a dead stream
                # cannot prevent container destruction.
                def _safe_yield(data):
                    """Return SSE string; caller wraps yield in try/except."""
                    return _emit(data)

                try:
                    yield _safe_yield({"type": "section_start", "name": "Cleanup", "test_key": f"{slug}_cleanup"})
                except Exception:
                    pass
                cleanup_status = "ok"

                # Remove tester sidecar (may already be gone if API auto-stop fired)
                if tester_container:
                    try:
                        await _run_blocking(tester_container.stop, timeout=3)
                        await _run_blocking(tester_container.remove, force=True)
                    except Exception:
                        pass  # already gone
                    try:
                        yield _safe_yield({"type": "line", "test_key": f"{slug}_cleanup", "timestamp": _ts(),
                                    "level": "ok", "message": "Test tools removed"})
                    except Exception:
                        pass

                # Destroy lab environment
                # Note: submit-flag API auto-stops the lab on correct submission,
                # so the session/containers may already be gone. Handle gracefully.
                if sim_session:
                    try:
                        db.refresh(sim_session)
                        already_stopped = sim_session.status == "stopped"
                    except Exception:
                        already_stopped = False

                    try:
                        await _run_blocking(docker_manager.destroy_lab_environment, user_id, slug)
                        if not already_stopped:
                            sim_session.status = "stopped"
                            sim_session.stopped_at = datetime.now(timezone.utc)
                            db.commit()
                    except Exception as e:
                        if not (already_stopped or flag_submitted_via_api):
                            cleanup_status = "warning"
                            logger.warning("Lab cleanup failed for %s: %s", slug, e)

                    try:
                        yield _safe_yield({"type": "line", "test_key": f"{slug}_cleanup", "timestamp": _ts(),
                                    "level": "ok", "message": "Lab environment destroyed"})
                    except Exception:
                        pass

                # Clean up test DB records created by the real API
                # (FlagAttempt + LabCompletion for this user+lab)
                if flag_submitted_via_api:
                    try:
                        cleaned = 0
                        attempts = db.query(FlagAttempt).filter(
                            FlagAttempt.user_id == user_id,
                            FlagAttempt.lab_id == lab["id"],
                        ).all()
                        for a in attempts:
                            db.delete(a)
                        cleaned += len(attempts)

                        completions = db.query(LabCompletion).filter(
                            LabCompletion.user_id == user_id,
                            LabCompletion.lab_id == lab["id"],
                        ).all()
                        for c in completions:
                            db.delete(c)
                        cleaned += len(completions)

                        if cleaned:
                            db.commit()
                    except Exception as db_err:
                        logger.warning("DB cleanup failed for %s: %s", slug, db_err)

                try:
                    yield _safe_yield({"type": "section_end", "test_key": f"{slug}_cleanup", "status": cleanup_status})
                except Exception:
                    pass

                # Lab result
                elapsed = time.monotonic() - lab_start
                overall_results[slug] = lab_status
                try:
                    yield _ev({"type": "lab_end", "lab_slug": slug, "status": lab_status,
                                "duration_seconds": round(elapsed, 1)})
                except Exception:
                    pass

                # Persist result to DB (upsert — newer replaces older)
                _persist_lab_result(lab, slug, lab_status, elapsed, admin_id, run_id)

        # ── Final summary ──────────────────────────────────────────────────
        _cancel_events.pop(run_id, None)

        completed = datetime.now(LOCAL_TZ)
        total_duration = (completed - started).total_seconds()
        passed = sum(1 for s in overall_results.values() if s == "ok")
        warned = sum(1 for s in overall_results.values() if s == "warning")
        failed = sum(1 for s in overall_results.values() if s in ("error", "cancelled"))
        skipped = sum(1 for s in overall_results.values() if s == "skipped")

        if is_cancelled():
            overall = "cancelled"
        elif failed > 0:
            overall = "error"
        elif warned > 0:
            overall = "warning"
        else:
            overall = "ok"

        yield _ev({
            "type": "complete",
            "overall": overall,
            "started_at": started.strftime("%H:%M:%S"),
            "completed_at": completed.strftime("%H:%M:%S"),
            "duration_seconds": round(total_duration, 1),
            "summary": {
                "total": len(lab_data),
                "passed": passed,
                "warned": warned,
                "failed": failed,
                "skipped": skipped,
                "results": overall_results,
            },
        })
        db.close()

    # ── Launch as background task instead of streaming response ─────────
    run_id = str(uuid.uuid4())[:8]
    cancel_event = asyncio.Event()
    _cancel_events[run_id] = cancel_event

    _prune_old_runs()

    # Source of truth is the file-based state (multi-worker safe). The
    # in-memory _active_runs entry only holds the asyncio task reference so it
    # is not garbage-collected on the worker that is actually running the test.
    _run_write_state(run_id, {
        "status": "running",
        "total_labs": len(labs),
        "labs_completed": 0,
        "current_lab": None,
        "current_lab_name": None,
        "started_at": _ts(),
        "started_epoch": time.time(),
        "summary": None,
        "admin_id": admin_id,
        "lab_slugs": [l.slug for l in labs],
    })

    # Detach Lab objects so they're usable after request ends
    lab_data = []
    for lab in labs:
        lab_data.append({
            "id": lab.id, "slug": lab.slug, "name": lab.name,
            "category": lab.category or "", "flag_hash": lab.flag_hash,
            "compose_file": lab.compose_file or "",
        })

    async def _background_task():
        """Run tests in background, persisting events/state to the shared run dir."""
        event_total = 0
        try:
            async for event_str in generate():
                if not isinstance(event_str, str):
                    continue
                # Parse SSE data lines into event dicts
                for line in event_str.strip().split("\n"):
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if event_total < MAX_RUN_EVENTS:
                        _run_append_event(run_id, data)
                        event_total += 1
                    # Update progress fields on milestone events only (bounded writes)
                    etype = data.get("type")
                    if etype in ("lab_start", "lab_end", "complete"):
                        state = _run_read_state(run_id) or {}
                        if etype == "lab_start":
                            state["current_lab"] = data.get("lab_slug")
                            state["current_lab_name"] = data.get("lab_name")
                        elif etype == "lab_end":
                            state["labs_completed"] = state.get("labs_completed", 0) + 1
                            state["current_lab"] = None
                            state["current_lab_name"] = None
                        elif etype == "complete":
                            state["summary"] = data.get("summary")
                            state["status"] = data.get("overall", "completed")
                        _run_write_state(run_id, state)
        except Exception as exc:
            logger.error("Background test runner error for run %s: %s", run_id, exc)
        finally:
            state = _run_read_state(run_id) or {}
            if state.get("status") == "running":
                state["status"] = "completed"
                _run_write_state(run_id, state)
            _cancel_events.pop(run_id, None)
            _active_runs.pop(run_id, None)

    # Hold the task reference on this worker so it isn't garbage-collected mid-run.
    _active_runs[run_id] = {"_task": asyncio.create_task(_background_task())}

    return {"run_id": run_id, "total_labs": len(labs), "status": "running"}


# ── Active run status + event polling ─────────────────────────────────────

@router.get("/exercise-test/active")
async def get_active_test_run(
    admin: User = Depends(get_current_instructor_user),
):
    """Return the currently active test run (if any). Reads file-based state so
    it works regardless of which worker handled the original POST."""
    try:
        names = os.listdir(_RUN_DIR)
    except FileNotFoundError:
        names = []
    running = []
    for name in names:
        if not name.endswith("_state.json"):
            continue
        rid = name[:-len("_state.json")]
        state = _run_read_state(rid)
        if state and state.get("status") == "running":
            running.append((rid, state))
    if running:
        # Most recently started run wins.
        running.sort(key=lambda rs: rs[1].get("started_epoch", 0), reverse=True)
        rid, state = running[0]
        _, total = _run_read_events(rid)
        return {
            "run_id": rid,
            "status": state["status"],
            "total_labs": state.get("total_labs", 0),
            "labs_completed": state.get("labs_completed", 0),
            "current_lab": state.get("current_lab"),
            "current_lab_name": state.get("current_lab_name"),
            "started_at": state.get("started_at"),
            "event_count": total,
            "lab_slugs": state.get("lab_slugs", []),
        }
    return {"run_id": None, "status": "idle"}


@router.get("/exercise-test/events/{run_id}")
async def get_test_events(
    run_id: str,
    after: int = 0,
    admin: User = Depends(get_current_instructor_user),
):
    """Return events for a run starting after index `after` (for polling).
    Reads file-based state so any worker can serve the poll."""
    state = _run_read_state(run_id)
    if not state:
        return {"run_id": run_id, "error": "not_found", "events": []}
    events, total = _run_read_events(run_id, after)
    return {
        "run_id": run_id,
        "status": state.get("status"),
        "total_labs": state.get("total_labs", 0),
        "labs_completed": state.get("labs_completed", 0),
        "current_lab": state.get("current_lab"),
        "current_lab_name": state.get("current_lab_name"),
        "event_count": total,
        "events": events,
    }


# ── Lab listing endpoint (for frontend dropdown) ──────────────────────────

@router.get("/exercise-test/labs")
async def list_testable_labs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_instructor_user),
):
    """Return list of all labs for the tester dropdown (includes inactive)."""
    query = db.query(Lab)
    labs = query.order_by(Lab.slug).all()

    # Pre-load course assignments for all labs in one query
    assignments = (
        db.query(CourseLabAssignment, Course)
        .join(Course, Course.id == CourseLabAssignment.course_id)
        .all()
    )
    lab_courses: Dict[int, list] = {}
    for cla, course in assignments:
        lab_courses.setdefault(cla.lab_id, []).append({
            "id": course.id,
            "name": course.name,
            "code": course.code,
        })

    result = []
    for lab in labs:
        lab_yaml = _load_lab_yaml(lab.slug)
        has_test_steps = bool(lab_yaml.get("test", {}).get("steps"))
        compose_yaml = _load_compose_yaml(lab.slug)
        has_services = bool(compose_yaml.get("services"))

        # Exclude labs that have no containers AND no test steps (interactive/RDP labs)
        if not has_services and not has_test_steps:
            continue

        result.append({
            "id": lab.id,
            "slug": lab.slug,
            "name": lab.name,
            "difficulty": lab.difficulty,
            "category": lab.category,
            "has_flag": bool(lab.flag_hash),
            "has_test_steps": has_test_steps,
            "track": lab.slug.split("-")[0] if "-" in lab.slug else "",
            "week": lab.week,
            "courses": lab_courses.get(lab.id, []),
        })
    return result


# ── Cancel endpoint ───────────────────────────────────────────────────────

@router.post("/exercise-test/cancel")
async def cancel_exercise_test(
    body: dict,
    admin: User = Depends(get_current_instructor_user),
):
    """Cancel a running exercise test by run_id. Sets a file flag the running
    task polls, so cancellation works even when this request is handled by a
    different worker than the one executing the run."""
    run_id = body.get("run_id", "")
    # Fast path if the running task happens to live on this worker.
    ev = _cancel_events.get(run_id)
    if ev:
        ev.set()
    if _run_request_cancel(run_id):
        return {"cancelled": True, "run_id": run_id}
    return {"cancelled": False, "message": "Run not found or already completed"}


# ── PDF report generation ─────────────────────────────────────────────────

class _ExerciseTestPDF(FPDF):
    """Custom PDF class for exercise test reports."""

    def __init__(self):
        super().__init__()
        self.report_title = "Exercise Test Report"

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"OpenCyberRange - {self.report_title}", ln=True, align="R")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _sanitize_for_pdf(text: str) -> str:
    """Replace Unicode characters that Helvetica/Courier can't render."""
    text = (
        text
        .replace("\u2192", "->")   # →
        .replace("\u2014", "--")   # —
        .replace("\u2013", "-")    # –
        .replace("\u2018", "'")    # '
        .replace("\u2019", "'")    # '
        .replace("\u201c", '"')    # "
        .replace("\u201d", '"')    # "
        .replace("\u2026", "...")  # …
        .replace("\u2022", "*")   # •
        .replace("\u00b7", ".")   # ·
    )
    # Strip any remaining non-Latin1 characters (Courier/Helvetica limit)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _generate_exercise_test_pdf(data: dict) -> bytes:
    """Generate a PDF report from exercise test result data.

    Args:
        data: {labName, category, date, status, duration, sections: [{name, status, lines}]}

    Returns:
        PDF file bytes.
    """
    pdf = _ExerciseTestPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    lab_name = _sanitize_for_pdf(data.get("labName", "Unknown"))
    category = _sanitize_for_pdf(data.get("category", ""))
    date_str = _sanitize_for_pdf(data.get("date", ""))
    status = data.get("status", "unknown")
    duration = data.get("duration", 0)
    sections = data.get("sections", [])

    # ── Status colors ──
    STATUS_COLORS = {
        "ok":      (34, 197, 94),     # green
        "warning": (245, 158, 11),    # amber
        "error":   (239, 68, 68),     # red
    }
    status_color = STATUS_COLORS.get(status, (100, 116, 139))
    status_label = {"ok": "PASSED", "warning": "WARNING", "error": "FAILED"}.get(status, status.upper())

    # ── Title row ──
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)
    title_w = pdf.get_string_width("Exercise Test Report") + 4
    badge_w = pdf.get_string_width(status_label) + 12
    pdf.cell(title_w, 12, "Exercise Test Report", ln=False)

    # Status badge
    x_badge = 210 - 10 - badge_w
    y_badge = pdf.get_y()
    pdf.set_xy(x_badge, y_badge)
    pdf.set_fill_color(*status_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(badge_w, 10, status_label, fill=True, align="C")
    pdf.ln(14)

    # Colored line under title
    pdf.set_draw_color(*status_color)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(8)

    # ── Meta info box ──
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    box_y = pdf.get_y()
    pdf.rect(10, box_y, 190, 28, style="DF")

    # Row 1: Exercise name (full width)
    pdf.set_xy(14, box_y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(24, 5, "Exercise:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 5, lab_name, ln=True)

    # Row 2: Category, Date, Duration
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(24, 5, "Category:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(36, 5, (category or "N/A").capitalize(), ln=False)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(14, 5, "Date:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(42, 5, date_str, ln=False)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(22, 5, "Duration:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    dur_str = f"{duration:.1f}s" if duration else "-"
    pdf.cell(0, 5, dur_str, ln=True)
    pdf.ln(10)

    # ── Sections ──
    LEVEL_COLORS = {
        "ok":      (22, 163, 74),     # green-600
        "error":   (220, 38, 38),     # red-600
        "warning": (217, 119, 6),     # amber-600
        "info":    (71, 85, 105),     # slate-600
    }

    for sec in sections:
        sec_name = _sanitize_for_pdf(sec.get("name", ""))
        sec_status = sec.get("status", "")
        lines = sec.get("lines", [])

        sec_color = STATUS_COLORS.get(sec_status, (100, 116, 139))

        # Section header bar
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(226, 232, 240)
        header_y = pdf.get_y()
        pdf.rect(10, header_y, 190, 7, style="DF")

        pdf.set_xy(12, header_y + 1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(140, 5, sec_name, ln=False)

        # Section status text
        sec_status_label = sec_status.upper() if sec_status else ""
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*sec_color)
        pdf.cell(0, 5, sec_status_label, ln=True, align="R")

        # Log lines
        if lines:
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            lines_y = pdf.get_y()

            pdf.set_font("Courier", "", 7)
            for idx, line in enumerate(lines):
                ts = line.get("timestamp", "")
                level = line.get("level", "info")
                msg = _sanitize_for_pdf(line.get("message", ""))
                color = LEVEL_COLORS.get(level, (71, 85, 105))

                # Alternating background
                if idx % 2 == 0:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.set_text_color(*color)
                text = f"{ts} {msg}" if ts else msg
                # Truncate long lines
                if len(text) > 120:
                    text = text[:117] + "..."
                pdf.cell(190, 3.5, text, ln=True, fill=True)

        pdf.ln(3)

        # Page break check
        if pdf.get_y() > 260:
            pdf.add_page()

    # ── Footer timestamp ──
    pdf.ln(6)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0, 6,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | OpenCyberRange",
        ln=True, align="C"
    )

    return pdf.output()


@router.post("/exercise-test/report")
async def generate_exercise_test_report(
    body: dict,
    admin: User = Depends(get_current_instructor_user),
):
    """Generate a PDF report from exercise test results.

    Body: {labName, category, date, status, duration, sections: [...]}
    Returns: PDF file download.
    """
    lab_name = body.get("labName", "exercise")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", lab_name.lower())
    filename = f"exercise_test_{safe_name}.pdf"

    pdf_bytes = _generate_exercise_test_pdf(body)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Persisted results endpoints ──────────────────────────────────────────

@router.get("/exercise-test/results")
async def get_exercise_test_results(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_instructor_user),
):
    """Return all saved exercise test results (latest per lab)."""
    query = db.query(ExerciseTestResult)
    rows = query.order_by(ExerciseTestResult.lab_slug).all()
    results = {}
    for r in rows:
        try:
            sections = json.loads(r.sections_json) if r.sections_json else []
        except (json.JSONDecodeError, TypeError):
            sections = []
        results[r.lab_slug] = {
            "status": r.status,
            "date": r.tested_at.strftime("%m/%d/%Y, %I:%M:%S %p") if r.tested_at else "",
            "labName": r.lab_name,
            "category": r.category or "",
            "track": r.track or "",
            "duration": r.duration_seconds,
            "sections": sections,
            "run_id": r.run_id,
            "tested_by_id": r.tested_by_id,
        }
    return results


@router.delete("/exercise-test/results/{lab_slug}")
async def delete_exercise_test_result(
    lab_slug: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_instructor_user),
):
    """Delete a single saved test result."""
    # Non-admin users can only delete results for their own labs
    if admin.role != 'admin':
        own_lab = db.query(Lab).filter(Lab.slug == lab_slug, Lab.created_by == admin.id).first()
        if not own_lab:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="You can only delete results for your own exercises")
    deleted = db.query(ExerciseTestResult).filter(
        ExerciseTestResult.lab_slug == lab_slug
    ).delete()
    db.commit()
    return {"deleted": deleted, "lab_slug": lab_slug}


@router.delete("/exercise-test/results")
async def clear_all_exercise_test_results(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_instructor_user),
):
    """Delete all saved test results."""
    if admin.role != 'admin':
        # Non-admin: only delete results for own labs
        own_slugs = [l.slug for l in db.query(Lab.slug).filter(Lab.created_by == admin.id).all()]
        deleted = db.query(ExerciseTestResult).filter(
            ExerciseTestResult.lab_slug.in_(own_slugs)
        ).delete(synchronize_session='fetch')
    else:
        deleted = db.query(ExerciseTestResult).delete()
    db.commit()
    return {"deleted": deleted}
