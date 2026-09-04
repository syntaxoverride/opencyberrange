#!/usr/bin/env python3
"""
OpenCyberRange Stress Test Tool

Simulates concurrent students hitting the platform to identify bottlenecks.

Usage (CLI):
    python stress_test.py --level 1 --users 45        # API-only (safe for production)
    python stress_test.py --level 2 --users 45        # API + auth flood
    python stress_test.py --level 3 --users 10        # Full load (spawns containers)
    python stress_test.py --level 4 --users 10        # RangeBox VNC load test
    python stress_test.py --cleanup                    # Remove test data
    python stress_test.py --level 1 --users 5 --quick # Quick smoke test

Programmatic (from backend endpoints):
    from stress_test import run_stress_test, cleanup_test_data
    run_stress_test(level=1, users=45, event_callback=my_callback)

Levels:
    1 = API stress test (no Docker, safe during production)
    2 = Auth + API flood (login storm, flag submissions, VPN polling)
    3 = Full load test (spawns real lab containers - idle system only!)
    4 = RangeBox VNC load test (spawns RangeBoxes, tests VNC connections)
"""

import argparse
import hashlib
import json
import os
import statistics
import struct
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

try:
    import websocket as ws_client  # websocket-client library
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

# --- Setup: import app modules for DB access and token generation ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.auth import create_access_token, get_password_hash
from app.database import SessionLocal
from app.models import (
    User, Lab, LabSession, LabCompletion, FlagAttempt,
    CourseEnrollment, ActivityEvent
)

# --- Constants ---
BASE_URL = "http://localhost:8000/api"
TEST_USER_PREFIX = "stresstest_"
TEST_PASSWORD = "StressTest2026!"
RAMP_UP_DELAY = 0.1  # seconds between user starts


class MetricsCollector:
    """Thread-safe metrics collection for API calls."""

    def __init__(self):
        self.results = defaultdict(list)  # endpoint -> [durations]
        self.errors = defaultdict(list)   # endpoint -> [error_msgs]
        self.status_codes = defaultdict(lambda: defaultdict(int))  # endpoint -> {code: count}

    def record(self, endpoint, duration, status_code, error=None):
        self.results[endpoint].append(duration)
        self.status_codes[endpoint][status_code] += 1
        if error:
            self.errors[endpoint].append(error)

    def to_dict(self):
        """Return results as a JSON-serializable dict for the UI."""
        endpoints = []
        threshold_failures = []

        for endpoint in sorted(self.results.keys()):
            durations = sorted(self.results[endpoint])
            n = len(durations)
            if n == 0:
                continue

            p50 = durations[int(n * 0.50)] if n > 0 else 0
            p95 = durations[int(n * 0.95)] if n > 1 else durations[-1]
            p99 = durations[int(n * 0.99)] if n > 1 else durations[-1]
            errs = len(self.errors[endpoint])

            is_slow_op = ("spawn" in endpoint.lower() or "stop" in endpoint.lower()
                          or "standalone/status" in endpoint.lower())
            threshold = 10.0 if is_slow_op else 2.0
            passed = p95 <= threshold

            if not passed:
                threshold_failures.append({
                    "endpoint": endpoint,
                    "p95": round(p95, 3),
                    "threshold": threshold,
                })

            endpoints.append({
                "endpoint": endpoint,
                "calls": n,
                "p50": round(p50, 3),
                "p95": round(p95, 3),
                "p99": round(p99, 3),
                "errors": errs,
                "passed": passed,
            })

        total_errors = sum(len(e) for e in self.errors.values())
        total_calls = sum(len(d) for d in self.results.values())
        error_rate = round((total_errors / total_calls * 100), 1) if total_calls > 0 else 0

        top_errors = []
        for ep in sorted(self.errors.keys()):
            for err in self.errors[ep][:3]:
                top_errors.append({"endpoint": ep, "error": err[:200]})

        return {
            "endpoints": endpoints,
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "error_rate_passed": error_rate <= 5,
            "threshold_failures": threshold_failures,
            "all_thresholds_passed": len(threshold_failures) == 0,
            "top_errors": top_errors,
        }

    def report(self):
        print("\n" + "=" * 70)
        print("  STRESS TEST RESULTS")
        print("=" * 70)

        # Header
        print(f"\n  {'Endpoint':<42} {'Calls':>5}  {'p50':>6}  {'p95':>6}  {'p99':>6}  {'Errs':>5}")
        print("  " + "-" * 66)

        threshold_failures = []

        for endpoint in sorted(self.results.keys()):
            durations = sorted(self.results[endpoint])
            n = len(durations)
            if n == 0:
                continue

            p50 = durations[int(n * 0.50)] if n > 0 else 0
            p95 = durations[int(n * 0.95)] if n > 1 else durations[-1]
            p99 = durations[int(n * 0.99)] if n > 1 else durations[-1]
            errs = len(self.errors[endpoint])

            print(f"  {endpoint:<42} {n:>5}  {p50:>5.2f}s  {p95:>5.2f}s  {p99:>5.2f}s  {errs:>5}")

            # Check thresholds
            is_slow_op = ("spawn" in endpoint.lower() or "stop" in endpoint.lower()
                          or "standalone/status" in endpoint.lower())
            threshold = 10.0 if is_slow_op else 2.0
            if p95 > threshold:
                threshold_failures.append(
                    f"  [FAIL] {endpoint} p95={p95:.2f}s (threshold: {threshold}s)"
                )

        # Error details
        total_errors = sum(len(e) for e in self.errors.values())
        total_calls = sum(len(d) for d in self.results.values())
        error_rate = (total_errors / total_calls * 100) if total_calls > 0 else 0

        print(f"\n  Total calls: {total_calls}  |  Errors: {total_errors} ({error_rate:.1f}%)")

        # Status code summary
        print(f"\n  Status Codes:")
        for endpoint in sorted(self.status_codes.keys()):
            codes = self.status_codes[endpoint]
            code_strs = [f"{code}:{count}" for code, count in sorted(codes.items())]
            print(f"    {endpoint:<42} {', '.join(code_strs)}")

        # Threshold results
        print(f"\n  THRESHOLD CHECKS:")
        if threshold_failures:
            for f in threshold_failures:
                print(f)
        else:
            print("  [PASS] All endpoints within acceptable response times")

        if error_rate > 5:
            print(f"  [FAIL] Error rate {error_rate:.1f}% exceeds 5% threshold")
        else:
            print(f"  [PASS] Error rate {error_rate:.1f}% within 5% threshold")

        # Print top errors
        if any(self.errors.values()):
            print(f"\n  TOP ERRORS:")
            for endpoint in sorted(self.errors.keys()):
                for err in self.errors[endpoint][:3]:
                    print(f"    {endpoint}: {err[:100]}")

        print("\n" + "=" * 70)


def api_call(session, method, path, metrics, label=None, **kwargs):
    """Make an API call and record metrics."""
    endpoint = label or f"{method.upper()} {path}"
    url = f"{BASE_URL}{path}"
    headers = kwargs.pop("headers", {})
    kwargs["headers"] = headers
    start = time.monotonic()
    try:
        resp = getattr(session, method)(url, timeout=120, **kwargs)
        duration = time.monotonic() - start
        error = None
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text[:100])
            except Exception:
                detail = resp.text[:100]
            error = f"HTTP {resp.status_code}: {detail}"
        metrics.record(endpoint, duration, resp.status_code, error)
        return resp
    except requests.exceptions.Timeout:
        duration = time.monotonic() - start
        metrics.record(endpoint, duration, 0, "TIMEOUT")
        return None
    except Exception as e:
        duration = time.monotonic() - start
        metrics.record(endpoint, duration, 0, str(e)[:100])
        return None


# --- Test User Management ---

def create_test_users(num_users, emit=None):
    """Create test users directly in the database."""
    db = SessionLocal()
    users = []
    hashed_pw = get_password_hash(TEST_PASSWORD)

    try:
        for i in range(1, num_users + 1):
            username = f"{TEST_USER_PREFIX}{i:03d}"
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                users.append(existing)
                continue

            user = User(
                username=username,
                email=f"{username}@stresstest.local",
                student_id=f"ST{i:04d}",
                hashed_password=hashed_pw,
                is_active=True,
                is_approved=True,
                role="student",
                must_change_password=False,
            )
            db.add(user)
            users.append(user)

        db.commit()
        # Refresh to get IDs
        for u in users:
            db.refresh(u)
        msg = f"Created/found {len(users)} test users"
        if emit:
            emit(msg)
        else:
            print(f"  {msg}")
        return [(u.id, u.username) for u in users]
    except Exception as e:
        db.rollback()
        msg = f"ERROR creating test users: {e}"
        if emit:
            emit(msg, level="error")
        else:
            print(f"  {msg}")
        return []
    finally:
        db.close()


def generate_tokens(user_list):
    """Generate JWT tokens for all test users."""
    tokens = {}
    for user_id, username in user_list:
        token = create_access_token(data={"sub": username})
        tokens[username] = {"token": token, "user_id": user_id}
    return tokens


def cleanup_test_data(emit=None):
    """Remove all stress test users and their associated data."""
    db = SessionLocal()
    try:
        test_users = db.query(User).filter(
            User.username.like(f"{TEST_USER_PREFIX}%")
        ).all()

        if not test_users:
            msg = "No test users found. Nothing to clean up."
            if emit:
                emit(msg)
            else:
                print(f"  {msg}")
            return

        user_ids = [u.id for u in test_users]
        msg = f"Found {len(test_users)} test users to remove"
        if emit:
            emit(msg)
        else:
            print(f"  {msg}")

        # Clean up related data
        deleted = db.query(LabSession).filter(LabSession.user_id.in_(user_ids)).delete(synchronize_session=False)
        if emit:
            emit(f"Deleted {deleted} lab sessions")
        else:
            print(f"    Deleted {deleted} lab sessions")

        deleted = db.query(LabCompletion).filter(LabCompletion.user_id.in_(user_ids)).delete(synchronize_session=False)
        if emit:
            emit(f"Deleted {deleted} lab completions")
        else:
            print(f"    Deleted {deleted} lab completions")

        deleted = db.query(FlagAttempt).filter(FlagAttempt.user_id.in_(user_ids)).delete(synchronize_session=False)
        if emit:
            emit(f"Deleted {deleted} flag attempts")
        else:
            print(f"    Deleted {deleted} flag attempts")

        deleted = db.query(ActivityEvent).filter(ActivityEvent.actor_id.in_(user_ids)).delete(synchronize_session=False)
        if emit:
            emit(f"Deleted {deleted} activity events")
        else:
            print(f"    Deleted {deleted} activity events")

        deleted = db.query(CourseEnrollment).filter(CourseEnrollment.user_id.in_(user_ids)).delete(synchronize_session=False)
        if emit:
            emit(f"Deleted {deleted} course enrollments")
        else:
            print(f"    Deleted {deleted} course enrollments")

        # Delete users
        for u in test_users:
            db.delete(u)

        db.commit()
        msg = f"Cleanup complete: removed {len(test_users)} test users and all related data"
        if emit:
            emit(msg)
        else:
            print(f"  {msg}")
    except Exception as e:
        db.rollback()
        msg = f"ERROR during cleanup: {e}"
        if emit:
            emit(msg, level="error")
        else:
            print(f"  {msg}")
        raise
    finally:
        db.close()


# --- Find a test lab ---

def find_test_lab(lab_slug=None):
    """Find a lab to use for testing. Returns (lab_id, lab_slug, flag_hash)."""
    db = SessionLocal()
    try:
        if lab_slug:
            lab = db.query(Lab).filter(Lab.slug == lab_slug, Lab.is_active == True).first()
        else:
            # Find the simplest active lab (beginner, shortest duration)
            lab = db.query(Lab).filter(
                Lab.is_active == True,
                Lab.difficulty == "beginner"
            ).order_by(Lab.duration_minutes).first()

            if not lab:
                lab = db.query(Lab).filter(Lab.is_active == True).first()

        if lab:
            return lab.id, lab.slug, lab.flag_hash
        return None, None, None
    finally:
        db.close()


# --- Level 1: API Stress Test ---

def student_workflow_level1(username, token_info, track_slugs, metrics):
    """Simulate a student browsing the platform (no Docker)."""
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token_info['token']}"

    # 1. Setup status (router guard - every navigation)
    api_call(session, "get", "/setup/status", metrics, "GET /setup/status")

    # 2. Dashboard
    api_call(session, "get", "/dashboard/student", metrics, "GET /dashboard/student")

    # 3. Browse tracks
    api_call(session, "get", "/exercises/tracks", metrics, "GET /exercises/tracks")

    # 4. View a specific track
    if track_slugs:
        slug = track_slugs[hash(username) % len(track_slugs)]
        api_call(session, "get", f"/exercises/tracks/{slug}", metrics, "GET /exercises/tracks/{slug}")

    # 5. VPN status poll
    api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")

    # 6. Courses list
    api_call(session, "get", "/courses/", metrics, "GET /courses/")

    # 7. Active session check
    api_call(session, "get", "/labs/active", metrics, "GET /labs/active")

    # 8. More setup/status polls (simulating navigation)
    for _ in range(3):
        api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
        time.sleep(0.05)

    # 9. Another VPN poll
    api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")

    session.close()


# --- Level 2: Auth + API Flood ---

def student_workflow_level2(username, token_info, track_slugs, lab_info, metrics):
    """Level 1 + login storm + flag submissions."""
    session = requests.Session()

    # 1. Login (tests auth throughput)
    resp = api_call(session, "post", "/auth/login", metrics, "POST /auth/login",
                    data={"username": username, "password": TEST_PASSWORD})

    # Use pre-generated token for remaining calls
    session.headers["Authorization"] = f"Bearer {token_info['token']}"

    # 2. Full Level 1 workflow
    api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
    api_call(session, "get", "/dashboard/student", metrics, "GET /dashboard/student")
    api_call(session, "get", "/exercises/tracks", metrics, "GET /exercises/tracks")

    if track_slugs:
        slug = track_slugs[hash(username) % len(track_slugs)]
        api_call(session, "get", f"/exercises/tracks/{slug}", metrics, "GET /exercises/tracks/{slug}")

    api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")
    api_call(session, "get", "/courses/", metrics, "GET /courses/")
    api_call(session, "get", "/labs/active", metrics, "GET /labs/active")

    # 3. Flag submission attempts (wrong flags)
    if lab_info and lab_info[0]:
        lab_id = lab_info[0]
        for i in range(3):
            api_call(session, "post", f"/exercises/labs/{lab_id}/submit-flag", metrics,
                     "POST /exercises/labs/{id}/submit-flag",
                     json={"flag": f"flag{{wrong_attempt_{i}}}"})
            time.sleep(0.1)

        # 4. Hint request
        api_call(session, "get", f"/exercises/labs/{lab_id}/hint", metrics,
                 "GET /exercises/labs/{id}/hint")

    # 5. VPN polling simulation (multiple polls)
    for _ in range(5):
        api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")
        api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
        time.sleep(0.2)

    session.close()


# --- Level 3: Full Load Test ---

def student_workflow_level3(username, token_info, track_slugs, lab_info, metrics, spawn_semaphore):
    """Full workflow including lab spawn and stop."""
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token_info['token']}"

    # 1. Pre-spawn workflow
    api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
    api_call(session, "get", "/dashboard/student", metrics, "GET /dashboard/student")
    api_call(session, "get", "/exercises/tracks", metrics, "GET /exercises/tracks")
    api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")

    if not lab_info or not lab_info[1]:
        session.close()
        return

    lab_slug = lab_info[1]

    # 2. Spawn lab (controlled concurrency)
    with spawn_semaphore:
        resp = api_call(session, "post", f"/labs/spawn/{lab_slug}", metrics,
                        "POST /labs/spawn/{slug}",
                        json={"rangebox": False})

    if resp and resp.status_code in (200, 201):
        # 3. Poll active session
        time.sleep(1)
        api_call(session, "get", "/labs/active", metrics, "GET /labs/active")

        # 4. Simulate working on lab (browsing, checking status)
        for _ in range(3):
            api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")
            api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
            time.sleep(1)

        # 5. Stop lab
        api_call(session, "post", "/labs/stop", metrics, "POST /labs/stop",
                 json={})

        # Wait for cleanup
        time.sleep(2)
    else:
        # Spawn failed - still do some API calls
        for _ in range(3):
            api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")
            time.sleep(0.5)

    session.close()


# --- Level 3: Pre-Spawn Helpers ---

def prespawn_labs(user_tokens, lab_slug, concurrent_spawns, emit, cancel_flag):
    """
    Pre-spawn labs for all test users before the timed phase.

    Returns:
        dict mapping username -> bool (True if spawn succeeded and lab is running)
    """
    spawn_results = {}
    spawn_lock = threading.Lock()
    total = len(user_tokens)
    completed = [0]

    def _spawn_one(username, token_info):
        if cancel_flag.is_set():
            return
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token_info['token']}"

        success = False
        try:
            resp = session.post(
                f"{BASE_URL}/labs/spawn/{lab_slug}",
                json={"rangebox": False},
                timeout=120,
            )
            success = resp.status_code in (200, 201)
            if not success:
                try:
                    detail = resp.json().get("detail", resp.text[:100])
                except Exception:
                    detail = resp.text[:100]
                emit(f"  Spawn HTTP {resp.status_code} for {username}: {detail}", level="warning")
        except Exception as e:
            emit(f"  Spawn failed for {username}: {e}", level="error")

        if success:
            # Poll until lab is running (max 60s)
            for _ in range(30):
                if cancel_flag.is_set():
                    break
                time.sleep(2)
                try:
                    r = session.get(f"{BASE_URL}/labs/active", timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        active = data.get("active_session")
                        if active and active.get("status") == "running":
                            break
                except Exception:
                    pass
            else:
                emit(f"  Lab for {username} never reached running state", level="warning")
                success = False

        with spawn_lock:
            spawn_results[username] = success
            completed[0] += 1
            n = completed[0]

        status = "OK" if success else "FAILED"
        emit(f"  Pre-spawn [{n}/{total}]: {username} {status}")
        session.close()

    emit(f"PRE-SPAWN PHASE: Spawning labs for {total} users "
         f"({concurrent_spawns} concurrent)...")

    with ThreadPoolExecutor(max_workers=concurrent_spawns) as executor:
        futures = []
        for username, token_info in user_tokens.items():
            if cancel_flag.is_set():
                break
            f = executor.submit(_spawn_one, username, token_info)
            futures.append(f)
            time.sleep(0.2)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                emit(f"  Pre-spawn worker error: {e}", level="error")

    succeeded = sum(1 for v in spawn_results.values() if v)
    failed = total - succeeded
    emit(f"Pre-spawn complete: {succeeded}/{total} labs running ({failed} failed)")

    return spawn_results


def cleanup_labs(user_tokens, spawn_results, emit, cancel_flag):
    """Stop labs for all users that were successfully pre-spawned."""
    to_stop = [u for u, ok in spawn_results.items() if ok]
    total = len(to_stop)
    if total == 0:
        emit("No labs to clean up")
        return

    stopped = [0]
    stop_lock = threading.Lock()

    def _stop_one(username):
        if cancel_flag.is_set():
            return
        token_info = user_tokens[username]
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token_info['token']}"
        try:
            session.post(f"{BASE_URL}/labs/stop", json={}, timeout=30)
        except Exception as e:
            emit(f"  Stop failed for {username}: {e}", level="warning")
        finally:
            session.close()
        with stop_lock:
            stopped[0] += 1
            n = stopped[0]
        if n % 10 == 0 or n == total:
            emit(f"  Cleanup [{n}/{total}] labs stopped")

    emit(f"CLEANUP PHASE: Stopping {total} labs...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_stop_one, u) for u in to_stop]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                emit(f"  Cleanup worker error: {e}", level="error")

    emit(f"Cleanup complete: {stopped[0]}/{total} labs stopped")


def student_workflow_level3_prespawned(username, token_info, track_slugs, lab_info, metrics):
    """
    Level 3 timed workflow with pre-spawned labs.
    Exercises API endpoints assuming the lab is already running.
    """
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token_info['token']}"

    # 1. Navigation / setup
    api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
    api_call(session, "get", "/dashboard/student", metrics, "GET /dashboard/student")

    # 2. Browse tracks
    api_call(session, "get", "/exercises/tracks", metrics, "GET /exercises/tracks")
    if track_slugs:
        slug = track_slugs[hash(username) % len(track_slugs)]
        api_call(session, "get", f"/exercises/tracks/{slug}", metrics,
                 "GET /exercises/tracks/{slug}")

    # 3. Check active lab session
    api_call(session, "get", "/labs/active", metrics, "GET /labs/active")

    # 4. VPN polling (simulates student checking connectivity)
    for _ in range(5):
        api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")
        api_call(session, "get", "/setup/status", metrics, "GET /setup/status")
        time.sleep(0.3)

    # 5. Courses list
    api_call(session, "get", "/courses/", metrics, "GET /courses/")

    # 6. Flag submission attempts (wrong flags — tests write path under load)
    if lab_info and lab_info[0]:
        lab_id = lab_info[0]
        for i in range(3):
            api_call(session, "post", f"/exercises/labs/{lab_id}/submit-flag", metrics,
                     "POST /exercises/labs/{id}/submit-flag",
                     json={"flag": f"flag{{wrong_attempt_{i}}}"})
            time.sleep(0.1)

        # 7. Hint request
        api_call(session, "get", f"/exercises/labs/{lab_id}/hint", metrics,
                 "GET /exercises/labs/{id}/hint")

    # 8. Additional active session + VPN polls (simulates ongoing work)
    for _ in range(3):
        api_call(session, "get", "/labs/active", metrics, "GET /labs/active")
        api_call(session, "get", "/labs/vpn-status", metrics, "GET /labs/vpn-status")
        time.sleep(0.5)

    session.close()


# --- Level 4: RangeBox VNC Load Test ---

def _get_host_stats():
    """Snapshot of host CPU and memory usage."""
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        parts = line.split()
        idle = int(parts[4])
        total = sum(int(p) for p in parts[1:])
    except Exception:
        idle, total = 0, 1

    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                k, v = line.split(":")
                mem[k.strip()] = int(v.strip().split()[0])
        mem_total = mem.get("MemTotal", 1)
        mem_avail = mem.get("MemAvailable", mem_total)
        mem_used_pct = round((1 - mem_avail / mem_total) * 100, 1)
    except Exception:
        mem_used_pct = 0.0

    return {"cpu_idle": idle, "cpu_total": total, "mem_used_pct": mem_used_pct}


def _compute_cpu_pct(before, after):
    """Compute host CPU usage % between two snapshots."""
    d_total = after["cpu_total"] - before["cpu_total"]
    d_idle = after["cpu_idle"] - before["cpu_idle"]
    if d_total <= 0:
        return 0.0
    return round((1 - d_idle / d_total) * 100, 1)


def _get_container_stats_batch(container_names):
    """Get CPU/memory stats for multiple containers via docker stats."""
    if not container_names:
        return {}
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream",
             "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.PIDs}}"]
            + list(container_names),
            capture_output=True, text=True, timeout=30,
        )
        stats = {}
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            name = parts[0].strip()
            cpu = parts[1].strip().rstrip("%")
            mem = parts[2].strip()
            pids = parts[3].strip()
            stats[name] = {
                "cpu_pct": float(cpu) if cpu else 0.0,
                "mem_usage": mem,
                "pids": int(pids) if pids.isdigit() else 0,
            }
        return stats
    except Exception:
        return {}


def _vnc_connect_and_measure(session, username, token_info, metrics,
                             duration_secs, cancel_flag, emit,
                             rangebox_ip=None):
    """
    Connect directly to a RangeBox's websockify and measure frame throughput
    and latency.  Bypasses the backend WebSocket proxy to avoid deadlocking
    uvicorn workers (the stress test threads run inside the same process).
    """
    if not HAS_WEBSOCKET:
        metrics.record("WS connect (VNC)", 0, 0, "websocket-client not installed")
        return

    if not rangebox_ip:
        metrics.record("WS connect (VNC)", 0, 0, "No RangeBox IP provided")
        return

    # Connect directly to the container's websockify (port 6080)
    ws_url = f"ws://{rangebox_ip}:6080/websockify"

    t_ws_start = time.monotonic()
    try:
        ws = ws_client.create_connection(
            ws_url,
            subprotocols=["binary"],
            timeout=15,
        )
        connect_time = time.monotonic() - t_ws_start
        metrics.record("WS connect (VNC)", connect_time, 200)
    except Exception as e:
        metrics.record("WS connect (VNC)", time.monotonic() - t_ws_start, 0,
                       f"WebSocket connect failed: {str(e)[:100]}")
        return

    # 3. Complete RFB handshake then measure frame throughput
    frames_received = 0
    bytes_received = 0
    first_frame_time = None
    handshake_ok = False
    try:
        ws.settimeout(10)

        # ── RFB Handshake ──
        # Step 1: Server sends version string (e.g. "RFB 003.008\n")
        ver = ws.recv()
        # Step 2: Client responds with same version
        if isinstance(ver, bytes):
            ws.send_binary(ver)
        else:
            ws.send(ver)

        # Step 3: Server sends security types
        sec = ws.recv()
        # Step 4: Client selects security type 1 (None/no auth)
        ws.send_binary(struct.pack("!B", 1))

        # Step 5: Server sends SecurityResult (4 bytes, 0 = OK)
        sec_result = ws.recv()

        # Step 6: Client sends ClientInit (shared=1)
        ws.send_binary(struct.pack("!B", 1))

        # Step 7: Server sends ServerInit (framebuffer dimensions, pixel format, name)
        server_init = ws.recv()
        handshake_ok = True

        # ── Request a full framebuffer update ──
        # FramebufferUpdateRequest: type=3, incremental=0, x=0, y=0, w=1280, h=800
        fbur = struct.pack("!BBHHHH", 3, 0, 0, 0, 1280, 800)
        ws.send_binary(fbur)

        # ── Read frames for the measurement period ──
        deadline = time.monotonic() + duration_secs
        ws.settimeout(5)

        while time.monotonic() < deadline:
            if cancel_flag and cancel_flag.is_set():
                break
            try:
                frame = ws.recv()
                if frame:
                    flen = len(frame) if isinstance(frame, (bytes, bytearray)) else len(frame.encode())
                    frames_received += 1
                    bytes_received += flen
                    if first_frame_time is None:
                        first_frame_time = time.monotonic() - t_ws_start
            except ws_client.WebSocketTimeoutException:
                # Request another update to keep the stream alive
                try:
                    fbur_inc = struct.pack("!BBHHHH", 3, 1, 0, 0, 1280, 800)
                    ws.send_binary(fbur_inc)
                except Exception:
                    pass
                continue
            except Exception:
                break

            # Periodically request incremental updates
            if frames_received % 10 == 0:
                try:
                    fbur_inc = struct.pack("!BBHHHH", 3, 1, 0, 0, 1280, 800)
                    ws.send_binary(fbur_inc)
                except Exception:
                    pass

        # ── Send a keystroke and measure response ──
        if handshake_ok:
            t_key = time.monotonic()
            try:
                # RFB KeyEvent: type=4, down-flag (1 byte), padding (2 bytes), key (4 bytes)
                key_down = struct.pack("!BBHI", 4, 1, 0, 0xff0d)
                key_up = struct.pack("!BBHI", 4, 0, 0, 0xff0d)
                ws.send_binary(key_down)
                ws.send_binary(key_up)
                # Request update to capture the screen change
                ws.send_binary(struct.pack("!BBHHHH", 3, 0, 0, 0, 1280, 800))

                ws.settimeout(3)
                try:
                    response_frame = ws.recv()
                    key_latency = time.monotonic() - t_key
                    metrics.record("VNC key-to-frame latency", key_latency, 200)
                except ws_client.WebSocketTimeoutException:
                    metrics.record("VNC key-to-frame latency", 3.0, 0,
                                   "Timeout waiting for frame after keystroke")
            except Exception as e:
                metrics.record("VNC key-to-frame latency", time.monotonic() - t_key, 0,
                               f"Keystroke failed: {str(e)[:80]}")

    except Exception as e:
        if not handshake_ok:
            metrics.record("VNC handshake", 0, 0,
                           f"RFB handshake failed: {str(e)[:80]}")
    finally:
        try:
            ws.close()
        except Exception:
            pass

    # Record throughput metrics
    if first_frame_time is not None:
        metrics.record("VNC first frame", first_frame_time, 200)
    else:
        metrics.record("VNC first frame", duration_secs, 0, "No frames received")

    elapsed = min(duration_secs, time.monotonic() - t_ws_start)
    fps = round(frames_received / max(elapsed, 0.1), 1)
    kbps = round(bytes_received / max(elapsed, 0.1) / 1024, 1)
    metrics.record(f"VNC throughput ({fps} fps, {kbps} KB/s)", 0.0, 200)


def prespawn_rangeboxes(user_tokens, concurrent_spawns, emit, cancel_flag):
    """Spawn standalone RangeBoxes for all test users."""
    spawn_results = {}
    spawn_lock = threading.Lock()
    total = len(user_tokens)
    completed = [0]

    def _spawn_one(username, token_info):
        if cancel_flag.is_set():
            return
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token_info['token']}"

        success = False
        try:
            resp = session.post(
                f"{BASE_URL}/rangebox/standalone/launch",
                timeout=120,
            )
            success = resp.status_code in (200, 201)
            if not success:
                try:
                    detail = resp.json().get("detail", resp.text[:100])
                except Exception:
                    detail = resp.text[:100]
                emit(f"  RangeBox spawn HTTP {resp.status_code} for {username}: {detail}",
                     level="warning")
        except Exception as e:
            emit(f"  RangeBox spawn failed for {username}: {e}", level="error")

        if success:
            # Poll until RangeBox is running (max 60s)
            for _ in range(30):
                if cancel_flag.is_set():
                    break
                time.sleep(2)
                try:
                    r = session.get(f"{BASE_URL}/rangebox/standalone/status", timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("status") == "running":
                            break
                except Exception:
                    pass
            else:
                emit(f"  RangeBox for {username} never reached running state",
                     level="warning")
                success = False

        with spawn_lock:
            spawn_results[username] = success
            completed[0] += 1
            n = completed[0]

        status_str = "OK" if success else "FAILED"
        emit(f"  RangeBox pre-spawn [{n}/{total}]: {username} {status_str}")
        session.close()

    emit(f"PRE-SPAWN PHASE: Launching {total} standalone RangeBoxes "
         f"({concurrent_spawns} concurrent)...")

    with ThreadPoolExecutor(max_workers=concurrent_spawns) as executor:
        futures = []
        for username, token_info in user_tokens.items():
            if cancel_flag.is_set():
                break
            f = executor.submit(_spawn_one, username, token_info)
            futures.append(f)
            time.sleep(0.3)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                emit(f"  RangeBox pre-spawn worker error: {e}", level="error")

    succeeded = sum(1 for v in spawn_results.values() if v)
    failed = total - succeeded
    emit(f"RangeBox pre-spawn complete: {succeeded}/{total} running ({failed} failed)")
    return spawn_results


def cleanup_rangeboxes(user_tokens, spawn_results, emit, cancel_flag):
    """Destroy standalone RangeBoxes for all spawned users."""
    to_stop = [u for u, ok in spawn_results.items() if ok]
    total = len(to_stop)
    if total == 0:
        emit("No RangeBoxes to clean up")
        return

    stopped = [0]
    stop_lock = threading.Lock()

    def _stop_one(username):
        if cancel_flag.is_set():
            return
        token_info = user_tokens[username]
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token_info['token']}"
        try:
            session.delete(f"{BASE_URL}/rangebox/standalone/destroy", timeout=30)
        except Exception as e:
            emit(f"  RangeBox destroy failed for {username}: {e}", level="warning")
        finally:
            session.close()
        with stop_lock:
            stopped[0] += 1
            n = stopped[0]
        if n % 5 == 0 or n == total:
            emit(f"  RangeBox cleanup [{n}/{total}] destroyed")

    emit(f"CLEANUP PHASE: Destroying {total} RangeBoxes...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_stop_one, u) for u in to_stop]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                emit(f"  RangeBox cleanup worker error: {e}", level="error")

    emit(f"RangeBox cleanup complete: {stopped[0]}/{total} destroyed")


# --- Programmatic Runner (for backend API) ---

def run_stress_test(level, users, concurrent_spawns=5, lab_slug=None,
                    event_callback=None, cancel_flag=None):
    """
    Run a stress test programmatically.

    Args:
        level: 1, 2, or 3
        users: number of concurrent users
        concurrent_spawns: max concurrent lab spawns (level 3 only)
        lab_slug: specific lab slug to test with
        event_callback: callable(event_dict) called for each progress event
        cancel_flag: threading.Event — set to cancel the test

    Returns:
        dict with full test results (metrics.to_dict())
    """
    if cancel_flag is None:
        cancel_flag = threading.Event()

    def emit(message, level="info"):
        if event_callback:
            event_callback({
                "type": "line",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": message,
            })

    level_names = {1: "API Stress Test", 2: "Auth + API Flood", 3: "Full Load Test",
                   4: "RangeBox VNC Load Test"}

    emit(f"Starting Level {level}: {level_names.get(level, 'Unknown')} with {users} users")

    if event_callback:
        event_callback({"type": "started", "level": level, "users": users})

    # Check cancellation
    if cancel_flag.is_set():
        emit("Test cancelled before start", level="warning")
        return {"cancelled": True}

    # Verify backend is reachable
    try:
        resp = requests.get(f"{BASE_URL}/setup/status", timeout=5)
        if resp.status_code != 200:
            emit(f"Backend returned {resp.status_code}. Is it running?", level="error")
            return {"error": "backend_unreachable"}
    except Exception as e:
        emit(f"Cannot reach backend at {BASE_URL}: {e}", level="error")
        return {"error": "backend_unreachable"}

    emit("Backend is reachable")

    # Setup test users
    emit(f"Creating {users} test users...")
    user_list = create_test_users(users, emit=emit)
    if not user_list:
        emit("Failed to create test users", level="error")
        return {"error": "user_creation_failed"}

    if cancel_flag.is_set():
        emit("Test cancelled during setup", level="warning")
        return {"cancelled": True}

    emit("Generating JWT tokens...")
    user_tokens = generate_tokens(user_list)

    metrics = MetricsCollector()

    # Discover tracks
    db = SessionLocal()
    from app.models import Track
    track_slugs = [t.slug for t in db.query(Track).filter(Track.is_active == True).all()]
    db.close()
    emit(f"Found {len(track_slugs)} active tracks: {', '.join(track_slugs)}")

    lab_info = None
    if level >= 2:
        lab_info = find_test_lab(lab_slug)
        emit(f"Test lab: {lab_info[1] or 'none (flag tests skipped)'}")

    if level == 3:
        emit(f"Concurrent spawns: {concurrent_spawns}")
        emit("WARNING: This will spawn real Docker containers!")

    if cancel_flag.is_set():
        emit("Test cancelled before execution", level="warning")
        return {"cancelled": True}

    # ── Level 3: Three-phase flow (pre-spawn → timed test → cleanup) ──

    if level == 3:
        if not lab_info or not lab_info[1]:
            emit("No test lab found. Level 3 requires a lab to spawn.", level="error")
            return {"error": "no_test_lab"}

        # ── Phase 0: Clean up stale sessions from previous runs ──
        emit("")
        emit("Cleaning up stale sessions from previous runs...")
        try:
            from app.database import SessionLocal as _SL
            from app.models import LabSession as _LS, User as _U
            _db = _SL()
            _stress_uids = [u.id for u in _db.query(_U).filter(_U.username.like("stresstest_%")).all()]
            _stale = _db.query(_LS).filter(
                _LS.user_id.in_(_stress_uids),
                _LS.status.in_(["starting", "running", "stopping"])
            ).all()
            if _stale:
                emit(f"  Found {len(_stale)} stale sessions, marking as stopped...")
                for _s in _stale:
                    _s.status = "stopped"
                _db.commit()
                # Stop orphaned containers
                import subprocess
                _orphans = subprocess.run(
                    ["docker", "ps", "--filter", "name=lab_", "--format", "{{.ID}}"],
                    capture_output=True, text=True, timeout=30
                )
                _ids = _orphans.stdout.strip().split("\n")
                _ids = [i for i in _ids if i]
                if _ids:
                    emit(f"  Removing {len(_ids)} orphaned containers...")
                    subprocess.run(["docker", "rm", "-f"] + _ids, capture_output=True, timeout=120)
                emit("  Cleanup complete")
            else:
                emit("  No stale sessions found")
            _db.close()
        except Exception as _e:
            emit(f"  Cleanup warning: {_e}", level="warning")

        # ── Phase 1: Pre-spawn (untimed) ──
        emit("")
        emit("=" * 50)
        emit("PHASE 1/3: Pre-spawning labs (not timed)")
        emit("=" * 50)

        if event_callback:
            event_callback({"type": "phase", "phase": "prespawn",
                            "phase_label": "Pre-spawning labs..."})

        spawn_results = prespawn_labs(
            user_tokens, lab_info[1], concurrent_spawns, emit, cancel_flag
        )

        if cancel_flag.is_set():
            emit("Test cancelled during pre-spawn", level="warning")
            cleanup_labs(user_tokens, spawn_results, emit, cancel_flag)
            return {"cancelled": True}

        ready_users = {u: t for u, t in user_tokens.items()
                       if spawn_results.get(u, False)}
        failed_count = len(user_tokens) - len(ready_users)

        if not ready_users:
            emit("All pre-spawns failed. Aborting test.", level="error")
            return {"error": "all_prespawns_failed"}

        if failed_count > 0:
            emit(f"WARNING: {failed_count} users failed to pre-spawn. "
                 f"Continuing with {len(ready_users)} users.", level="warning")

        # ── Phase 2: Timed test ──
        emit("")
        emit("=" * 50)
        emit(f"PHASE 2/3: Timed API test ({len(ready_users)} users with live labs)")
        emit("=" * 50)

        if event_callback:
            event_callback({"type": "phase", "phase": "timed",
                            "phase_label": "Running timed test..."})

        effective_users = len(ready_users)
        metrics = MetricsCollector()  # Fresh collector — timed phase only
        start_time = time.monotonic()
        completed_users = 0
        completed_lock = threading.Lock()

        def _user_done_l3(username):
            nonlocal completed_users
            with completed_lock:
                completed_users += 1
                n = completed_users
            if event_callback:
                event_callback({
                    "type": "progress",
                    "completed": n,
                    "total": effective_users,
                    "username": username,
                })

        with ThreadPoolExecutor(max_workers=effective_users) as executor:
            futures = []
            for username, token_info in ready_users.items():
                if cancel_flag.is_set():
                    break

                def _run(u=username, t=token_info):
                    if cancel_flag.is_set():
                        return
                    student_workflow_level3_prespawned(
                        u, t, track_slugs, lab_info, metrics
                    )
                    _user_done_l3(u)

                f = executor.submit(_run)
                futures.append(f)
                time.sleep(RAMP_UP_DELAY)

            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    emit(f"Worker error: {e}", level="error")

        duration = time.monotonic() - start_time

        if cancel_flag.is_set():
            emit(f"Timed phase cancelled after {duration:.1f}s "
                 f"({completed_users}/{effective_users} users)", level="warning")
        else:
            emit(f"Timed phase completed in {duration:.1f}s")

        # ── Phase 3: Cleanup (untimed) ──
        emit("")
        emit("=" * 50)
        emit("PHASE 3/3: Cleaning up labs (not timed)")
        emit("=" * 50)

        if event_callback:
            event_callback({"type": "phase", "phase": "cleanup",
                            "phase_label": "Cleaning up labs..."})

        cleanup_labs(user_tokens, spawn_results, emit, cancel_flag)

        # Build results (timed phase only)
        results = metrics.to_dict()
        results["level"] = level
        results["users"] = users
        results["concurrent_spawns"] = concurrent_spawns
        results["effective_users"] = effective_users
        results["prespawn_total"] = users
        results["prespawn_succeeded"] = effective_users
        results["prespawn_failed"] = failed_count
        results["duration_seconds"] = round(duration, 1)
        results["cancelled"] = cancel_flag.is_set()

        # Pre-spawn health: if many spawns failed, the test is not meaningful
        prespawn_rate = effective_users / max(users, 1)
        results["prespawn_pass"] = prespawn_rate >= 0.75
        if not results["prespawn_pass"]:
            results["all_thresholds_passed"] = False
            pct = round(prespawn_rate * 100)
            results["threshold_failures"].append({
                "endpoint": "PRE-SPAWN",
                "p95": 0,
                "threshold": 0,
                "detail": f"Only {effective_users}/{users} labs spawned ({pct}%) - Docker subnet pool exhausted",
            })

    # ── Level 4: RangeBox VNC Load Test ─────────────────────────────────

    elif level == 4:
        if not HAS_WEBSOCKET:
            emit("ERROR: websocket-client package is required for Level 4. "
                 "Install with: pip install websocket-client", level="error")
            return {"error": "missing_dependency"}

        emit(f"Concurrent spawns: {concurrent_spawns}")
        emit("WARNING: This will spawn standalone RangeBox containers!")

        if cancel_flag.is_set():
            emit("Test cancelled before RangeBox spawn", level="warning")
            return {"cancelled": True}

        # ── Phase 1: Pre-spawn RangeBoxes ──
        emit("")
        emit("=" * 50)
        emit("PHASE 1/3: Spawning standalone RangeBoxes (not timed)")
        emit("=" * 50)

        if event_callback:
            event_callback({"type": "phase", "phase": "prespawn",
                            "phase_label": "Spawning RangeBoxes..."})

        spawn_results = prespawn_rangeboxes(
            user_tokens, concurrent_spawns, emit, cancel_flag
        )

        if cancel_flag.is_set():
            emit("Test cancelled during RangeBox spawn", level="warning")
            cleanup_rangeboxes(user_tokens, spawn_results, emit, cancel_flag)
            return {"cancelled": True}

        ready_users = {u: t for u, t in user_tokens.items()
                       if spawn_results.get(u, False)}
        failed_count = len(user_tokens) - len(ready_users)

        if not ready_users:
            emit("All RangeBox spawns failed. Aborting test.", level="error")
            return {"error": "all_rangebox_spawns_failed"}

        if failed_count > 0:
            emit(f"WARNING: {failed_count} RangeBoxes failed to spawn. "
                 f"Continuing with {len(ready_users)} users.", level="warning")

        # ── Phase 2: VNC connection test ──
        emit("")
        emit("=" * 50)
        emit(f"PHASE 2/3: VNC load test ({len(ready_users)} concurrent connections)")
        emit("=" * 50)

        if event_callback:
            event_callback({"type": "phase", "phase": "timed",
                            "phase_label": "Testing VNC connections..."})

        # Capture host stats before test
        host_before = _get_host_stats()
        emit(f"Host memory usage before: {host_before['mem_used_pct']}%")

        effective_users = len(ready_users)
        metrics = MetricsCollector()
        start_time = time.monotonic()
        completed_users = 0
        completed_lock = threading.Lock()

        vnc_test_duration = 15  # seconds per VNC session

        def _user_done_l4(username):
            nonlocal completed_users
            with completed_lock:
                completed_users += 1
                n = completed_users
            if event_callback:
                event_callback({
                    "type": "progress",
                    "completed": n,
                    "total": effective_users,
                    "username": username,
                })

        # Collect container stats mid-test in a background thread
        container_stats_result = [None]
        def _collect_stats():
            time.sleep(vnc_test_duration // 2)  # sample mid-test
            names = [f"rangebox_{t['user_id']}_standalone"
                     for t in ready_users.values()]
            container_stats_result[0] = _get_container_stats_batch(names)

        stats_thread = threading.Thread(target=_collect_stats, daemon=True)
        stats_thread.start()

        with ThreadPoolExecutor(max_workers=effective_users) as executor:
            futures = []
            for username, token_info in ready_users.items():
                if cancel_flag.is_set():
                    break

                def _run(u=username, t=token_info):
                    if cancel_flag.is_set():
                        return
                    session = requests.Session()
                    session.headers["Authorization"] = f"Bearer {t['token']}"
            
                    # Compute the direct RangeBox IP (bypasses backend proxy)
                    uid = t["user_id"]
                    octet = (uid % 240) + 10
                    rb_ip = f"10.50.{octet}.10"

                    # Also do basic API calls while VNC is connected
                    api_call(session, "get", "/setup/status", metrics,
                             "GET /setup/status")
                    api_call(session, "get", "/rangebox/standalone/status", metrics,
                             "GET /rangebox/standalone/status")

                    _vnc_connect_and_measure(
                        session, u, t, metrics,
                        vnc_test_duration, cancel_flag, emit,
                        rangebox_ip=rb_ip,
                    )

                    # Post-VNC API responsiveness check
                    api_call(session, "get", "/setup/status", metrics,
                             "GET /setup/status (under VNC load)")

                    session.close()
                    _user_done_l4(u)

                f = executor.submit(_run)
                futures.append(f)
                time.sleep(0.2)  # stagger connections

            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    emit(f"VNC worker error: {e}", level="error")

        duration = time.monotonic() - start_time

        # Wait for stats collection to finish
        stats_thread.join(timeout=5)

        # Capture host stats after test
        host_after = _get_host_stats()
        host_cpu_pct = _compute_cpu_pct(host_before, host_after)

        emit(f"")
        emit(f"Host CPU usage during test: {host_cpu_pct}%")
        emit(f"Host memory usage after: {host_after['mem_used_pct']}%")

        # Report per-container stats
        cstats = container_stats_result[0]
        if cstats:
            emit("")
            emit("Per-container stats (mid-test snapshot):")
            total_cpu = 0
            for cname, cs in sorted(cstats.items()):
                emit(f"  {cname}: CPU {cs['cpu_pct']}%, "
                     f"Mem {cs['mem_usage']}, PIDs {cs['pids']}")
                total_cpu += cs["cpu_pct"]
            emit(f"  Total container CPU: {round(total_cpu, 1)}%")

        if cancel_flag.is_set():
            emit(f"VNC test cancelled after {duration:.1f}s "
                 f"({completed_users}/{effective_users} users)", level="warning")
        else:
            emit(f"VNC test completed in {duration:.1f}s")

        # ── Phase 3: Cleanup ──
        emit("")
        emit("=" * 50)
        emit("PHASE 3/3: Destroying RangeBoxes (not timed)")
        emit("=" * 50)

        if event_callback:
            event_callback({"type": "phase", "phase": "cleanup",
                            "phase_label": "Destroying RangeBoxes..."})

        cleanup_rangeboxes(user_tokens, spawn_results, emit, cancel_flag)

        # Build results
        results = metrics.to_dict()
        results["level"] = level
        results["users"] = users
        results["concurrent_spawns"] = concurrent_spawns
        results["effective_users"] = effective_users
        results["prespawn_total"] = users
        results["prespawn_succeeded"] = effective_users
        results["prespawn_failed"] = failed_count
        results["duration_seconds"] = round(duration, 1)
        results["cancelled"] = cancel_flag.is_set()
        results["host_cpu_pct"] = host_cpu_pct
        results["host_mem_pct"] = host_after["mem_used_pct"]

        if cstats:
            results["container_stats"] = cstats

        # Pre-spawn health check
        prespawn_rate = effective_users / max(users, 1)
        results["prespawn_pass"] = prespawn_rate >= 0.75
        if not results["prespawn_pass"]:
            results["all_thresholds_passed"] = False
            pct = round(prespawn_rate * 100)
            results["threshold_failures"].append({
                "endpoint": "RANGEBOX PRE-SPAWN",
                "p95": 0,
                "threshold": 0,
                "detail": f"Only {effective_users}/{users} RangeBoxes spawned ({pct}%)",
            })

        # Host CPU threshold: warn if above 85%
        if host_cpu_pct > 85:
            results["all_thresholds_passed"] = False
            results["threshold_failures"].append({
                "endpoint": "HOST CPU",
                "p95": host_cpu_pct,
                "threshold": 85,
                "detail": f"Host CPU at {host_cpu_pct}% (threshold: 85%)",
            })

    # ── Levels 1 & 2: existing single-phase flow ──

    else:
        emit(f"Starting concurrent requests...")

        start_time = time.monotonic()
        completed_users = 0
        completed_lock = threading.Lock()

        def _user_done(username):
            nonlocal completed_users
            with completed_lock:
                completed_users += 1
                n = completed_users
            if event_callback:
                event_callback({
                    "type": "progress",
                    "completed": n,
                    "total": users,
                    "username": username,
                })

        def _wrapped_workflow_level1(username, token_info, track_slugs, metrics):
            if cancel_flag.is_set():
                return
            student_workflow_level1(username, token_info, track_slugs, metrics)
            _user_done(username)

        def _wrapped_workflow_level2(username, token_info, track_slugs, lab_info, metrics):
            if cancel_flag.is_set():
                return
            student_workflow_level2(username, token_info, track_slugs, lab_info, metrics)
            _user_done(username)

        with ThreadPoolExecutor(max_workers=users) as executor:
            futures = []

            for i, (username, token_info) in enumerate(user_tokens.items()):
                if i >= users:
                    break
                if cancel_flag.is_set():
                    emit("Cancelling remaining user submissions", level="warning")
                    break

                if level == 1:
                    f = executor.submit(_wrapped_workflow_level1, username, token_info, track_slugs, metrics)
                elif level == 2:
                    f = executor.submit(_wrapped_workflow_level2, username, token_info, track_slugs, lab_info, metrics)
                futures.append(f)
                time.sleep(RAMP_UP_DELAY)

            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    emit(f"Worker error: {e}", level="error")

        duration = time.monotonic() - start_time

        if cancel_flag.is_set():
            emit(f"Test cancelled after {duration:.1f}s ({completed_users}/{users} users completed)", level="warning")
        else:
            emit(f"Level {level} completed in {duration:.1f}s")

        # Build results
        results = metrics.to_dict()
        results["level"] = level
        results["users"] = users
        results["concurrent_spawns"] = concurrent_spawns
        results["duration_seconds"] = round(duration, 1)
        results["cancelled"] = cancel_flag.is_set()

    # Emit endpoint results for live table updates
    if event_callback:
        for ep in results["endpoints"]:
            event_callback({
                "type": "endpoint_result",
                "endpoint": ep["endpoint"],
                "calls": ep["calls"],
                "p50": ep["p50"],
                "p95": ep["p95"],
                "p99": ep["p99"],
                "errors": ep["errors"],
                "passed": ep["passed"],
            })

    # Emit complete event
    if event_callback:
        event_callback({
            "type": "complete",
            "results": results,
        })

    return results


# --- Test Runners (CLI mode) ---

def run_level1(user_tokens, metrics, num_users):
    """Run Level 1: API-only stress test."""
    # Discover tracks
    db = SessionLocal()
    from app.models import Track
    track_slugs = [t.slug for t in db.query(Track).filter(Track.is_active == True).all()]
    db.close()

    print(f"\n  Level 1: API Stress Test ({num_users} users, no Docker)")
    print(f"  Tracks found: {track_slugs}")
    print(f"  Starting concurrent requests...\n")

    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        for i, (username, token_info) in enumerate(user_tokens.items()):
            if i >= num_users:
                break
            f = executor.submit(student_workflow_level1, username, token_info, track_slugs, metrics)
            futures.append(f)
            time.sleep(RAMP_UP_DELAY)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"  Worker error: {e}")

    duration = time.monotonic() - start_time
    print(f"\n  Level 1 completed in {duration:.1f}s")


def run_level2(user_tokens, metrics, num_users, lab_slug=None):
    """Run Level 2: Auth + API flood."""
    db = SessionLocal()
    from app.models import Track
    track_slugs = [t.slug for t in db.query(Track).filter(Track.is_active == True).all()]
    db.close()

    lab_info = find_test_lab(lab_slug)
    print(f"\n  Level 2: Auth + API Flood ({num_users} users)")
    print(f"  Test lab: {lab_info[1] or 'none (flag tests skipped)'}")
    print(f"  Starting concurrent requests...\n")

    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        for i, (username, token_info) in enumerate(user_tokens.items()):
            if i >= num_users:
                break
            f = executor.submit(student_workflow_level2, username, token_info,
                                track_slugs, lab_info, metrics)
            futures.append(f)
            time.sleep(RAMP_UP_DELAY)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"  Worker error: {e}")

    duration = time.monotonic() - start_time
    print(f"\n  Level 2 completed in {duration:.1f}s")


def run_level3(user_tokens, metrics, num_users, concurrent_spawns=5, lab_slug=None):
    """Run Level 3: Full load test with Docker."""
    db = SessionLocal()
    from app.models import Track
    track_slugs = [t.slug for t in db.query(Track).filter(Track.is_active == True).all()]
    db.close()

    lab_info = find_test_lab(lab_slug)
    spawn_semaphore = threading.Semaphore(concurrent_spawns)

    print(f"\n  Level 3: Full Load Test ({num_users} users, {concurrent_spawns} concurrent spawns)")
    print(f"  Test lab: {lab_info[1] or 'none (spawn tests skipped)'}")
    print(f"  WARNING: This will spawn real Docker containers!")
    print(f"  Starting concurrent requests...\n")

    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        for i, (username, token_info) in enumerate(user_tokens.items()):
            if i >= num_users:
                break
            f = executor.submit(student_workflow_level3, username, token_info,
                                track_slugs, lab_info, metrics, spawn_semaphore)
            futures.append(f)
            time.sleep(RAMP_UP_DELAY)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"  Worker error: {e}")

    duration = time.monotonic() - start_time
    print(f"\n  Level 3 completed in {duration:.1f}s")


# --- DB Metrics ---

def print_db_metrics():
    """Print current database connection stats."""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        result = db.execute(text(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )).scalar()
        print(f"\n  DB Connections: {result}")

        result = db.execute(text(
            "SELECT state, count(*) FROM pg_stat_activity "
            "WHERE datname = current_database() GROUP BY state"
        )).fetchall()
        for state, count in result:
            print(f"    {state or 'null'}: {count}")
    except Exception as e:
        print(f"  Could not fetch DB metrics: {e}")
    finally:
        db.close()


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="OpenCyberRange Stress Test Tool")
    parser.add_argument("--level", type=int, choices=[1, 2, 3, 4], default=1,
                        help="Test level (1=API, 2=Auth+API, 3=Full+Docker, 4=RangeBox VNC)")
    parser.add_argument("--users", type=int, default=45,
                        help="Number of concurrent test users (default: 45)")
    parser.add_argument("--concurrent-spawns", type=int, default=5,
                        help="Max concurrent lab spawns for level 3 (default: 5)")
    parser.add_argument("--lab-slug", type=str, default=None,
                        help="Specific lab slug to test with")
    parser.add_argument("--cleanup", action="store_true",
                        help="Remove all test users and data, then exit")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: reduce iterations per user")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  OpenCyberRange Stress Test Tool")
    print("=" * 70)

    if args.cleanup:
        print("\n  Cleaning up test data...")
        cleanup_test_data()
        return

    # Verify backend is reachable
    try:
        resp = requests.get(f"{BASE_URL}/setup/status", timeout=5)
        if resp.status_code != 200:
            print(f"\n  ERROR: Backend returned {resp.status_code}. Is it running?")
            return
    except Exception as e:
        print(f"\n  ERROR: Cannot reach backend at {BASE_URL}: {e}")
        return

    print(f"\n  Configuration:")
    print(f"    Level: {args.level}")
    print(f"    Users: {args.users}")
    if args.level == 3:
        print(f"    Concurrent spawns: {args.concurrent_spawns}")
    if args.lab_slug:
        print(f"    Lab: {args.lab_slug}")

    # Setup
    print(f"\n  Setting up test users...")
    user_list = create_test_users(args.users)
    if not user_list:
        print("  ERROR: Failed to create test users")
        return

    print(f"  Generating JWT tokens...")
    user_tokens = generate_tokens(user_list)

    metrics = MetricsCollector()

    # Run the test
    if args.level == 1:
        run_level1(user_tokens, metrics, args.users)
    elif args.level == 2:
        run_level2(user_tokens, metrics, args.users, args.lab_slug)
    elif args.level == 3:
        run_level3(user_tokens, metrics, args.users, args.concurrent_spawns, args.lab_slug)
    elif args.level == 4:
        # Level 4 uses the programmatic runner (handles all phases internally)
        def _cli_emit(event):
            if event.get("type") == "line":
                print(f"  {event.get('message', '')}")
            elif event.get("type") == "complete":
                result = event.get("results", {})
                # Build a MetricsCollector from the result for the standard report
                for ep in result.get("endpoints", []):
                    metrics.results[ep["endpoint"]] = [ep["p50"]] * max(1, ep["calls"])
                    if ep["errors"] > 0:
                        metrics.errors[ep["endpoint"]] = [f"errors: {ep['errors']}"]

        result = run_stress_test(
            level=4,
            users=args.users,
            concurrent_spawns=args.concurrent_spawns,
            event_callback=_cli_emit,
        )
        if result and result.get("host_cpu_pct") is not None:
            print(f"\n  Host CPU: {result['host_cpu_pct']}%")
            print(f"  Host Memory: {result.get('host_mem_pct', 'N/A')}%")

    # Report
    metrics.report()
    print_db_metrics()

    print(f"\n  Tip: Run 'python stress_test.py --cleanup' to remove test data\n")


if __name__ == "__main__":
    main()
