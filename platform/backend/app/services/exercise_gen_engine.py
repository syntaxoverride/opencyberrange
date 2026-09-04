"""Exercise Studio generation worker (Phase 2).

A durable, DB-backed background worker (PRD 5.7). It advances generation jobs
and items with a Postgres claim-and-lease so it is safe across the 17 uvicorn
workers (each runs start_scheduler). It never holds state in memory: the job is
the rows, the browser only observes.

Lifecycle:
  job.planning      -> worker claims, calls the model to plan, creates items,
                       job.awaiting_plan
  (instructor approves the plan via the endpoint) -> job.building
  job.building      -> worker claims each pending item, generates cosmetic
                       overrides, then materialize -> gate -> ingest -> stage a
                       TemplateInstance + StudioPendingReview (the SAME path a
                       manual reskin uses). item.ready / failed / needs_infra.
  all items terminal -> job.awaiting_review

The heavy per-step work (model call, docker-less render, lint gate, discover)
runs in a thread executor so the event loop is never blocked.
"""
import asyncio
import json
import logging
import os
import shutil
import socket
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.database import SessionLocal
from app.services import template_engine, studio_publish, exercise_writer

logger = logging.getLogger(__name__)

POLL_SECONDS = 5
LEASE_SECONDS = 180
_WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Atomic claim helpers (FOR UPDATE SKIP LOCKED -> only one worker wins)
# ---------------------------------------------------------------------------

def _claim_planning_job(db):
    row = db.execute(
        text(
            """
            UPDATE exercise_gen_jobs SET claimed_by = :w, lease_until = :lease
            WHERE id = (
                SELECT id FROM exercise_gen_jobs
                WHERE status = 'planning'
                  AND (lease_until IS NULL OR lease_until < :now)
                ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
            )
            RETURNING id
            """
        ),
        {"w": _WORKER_ID, "lease": _now() + timedelta(seconds=LEASE_SECONDS), "now": _now()},
    ).fetchone()
    db.commit()
    return row[0] if row else None


def _claim_building_item(db):
    row = db.execute(
        text(
            """
            UPDATE exercise_gen_items SET claimed_by = :w, lease_until = :lease,
                   status = 'building'
            WHERE id = (
                SELECT i.id FROM exercise_gen_items i
                JOIN exercise_gen_jobs j ON j.id = i.job_id
                WHERE i.status = 'pending' AND j.status = 'building'
                  AND (i.lease_until IS NULL OR i.lease_until < :now)
                ORDER BY i.id LIMIT 1 FOR UPDATE SKIP LOCKED
            )
            RETURNING id
            """
        ),
        {"w": _WORKER_ID, "lease": _now() + timedelta(seconds=LEASE_SECONDS), "now": _now()},
    ).fetchone()
    db.commit()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def _plan_job(job_id):
    from app.models import ExerciseGenJob, ExerciseGenItem
    db = SessionLocal()
    try:
        job = db.get(ExerciseGenJob, job_id)
        if not job or job.status != "planning":
            return
        conn = exercise_writer.resolve_connection(
            db, job.instructor_id, getattr(job, "provider_profile_id", None)
        )
        params = {}
        try:
            params = json.loads(job.params or "{}")
        except (json.JSONDecodeError, ValueError):
            params = {}
        catalog = template_engine.list_templates()
        try:
            items, tokens = exercise_writer.plan_exercises(
                conn, job.input_syllabus, params, catalog
            )
        except Exception as e:
            logger.warning("gen plan failed for job %s: %s", job_id, e)
            job.status = "failed"
            job.error = f"planning failed: {e}"[:500]
            job.claimed_by = None
            job.lease_until = None
            db.commit()
            return
        for it in items:
            has_template = bool(it.get("template_slug"))
            db.add(ExerciseGenItem(
                job_id=job.id,
                title=it["title"],
                technique=it["technique"],
                tier=it["tier"],
                template_slug=it["template_slug"] or None,
                stage="select",
                # No catalog match -> parked for Phase 3, not built now.
                status="pending" if has_template else "needs_infra",
                error=None if has_template else "no catalog template fits (Phase 3 / author)",
            ))
        job.token_cost = (job.token_cost or 0) + (tokens or 0)
        job.status = "awaiting_plan"
        job.claimed_by = None
        job.lease_until = None
        db.commit()
        logger.info("gen job %s planned %d item(s)", job_id, len(items))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Building one item: generate overrides -> materialize -> gate -> ingest -> stage
# ---------------------------------------------------------------------------

def _build_item(item_id):
    from app.models import (
        ExerciseGenJob, ExerciseGenItem, ExerciseTemplate,
        TemplateInstance, StudioPendingReview,
    )
    db = SessionLocal()
    lab_dir = None
    try:
        item = db.get(ExerciseGenItem, item_id)
        if not item or item.status != "building":
            return
        job = db.get(ExerciseGenJob, item.job_id)
        template_row = (
            db.query(ExerciseTemplate)
            .filter(ExerciseTemplate.slug == item.template_slug)
            .one_or_none()
        )
        if template_row is None:
            item.status = "failed"
            item.error = "template not registered in catalog"
            db.commit()
            return
        try:
            conn = exercise_writer.resolve_connection(
                db, job.instructor_id, getattr(job, "provider_profile_id", None)
            )
            template = template_engine.get_template(item.template_slug)
            overrides, tokens = exercise_writer.generate_overrides(
                conn, {"title": item.title, "technique": item.technique},
                template,
            )
            item.overrides = json.dumps(overrides)
            item.stage = "generate"
            db.commit()

            result = template_engine.materialize_instance(item.template_slug, overrides)
            lab_dir = result.get("lab_dir")
            item.stage = "gate"
            db.commit()

            gate = studio_publish.run_gate(lab_dir, fork_type="cosmetic")
            if not gate.get("passed"):
                shutil.rmtree(lab_dir, ignore_errors=True)
                lab_dir = None
                item.status = "failed"
                item.error = f"gate failed: {gate.get('summary', '')}"[:300]
                db.commit()
                return

            item.stage = "ingest"
            db.commit()
            ingest = template_engine.ingest_draft_lab(result["lab_slug"])
            lab_id = ingest.get("lab_id") if ingest else None
            if not lab_id:
                shutil.rmtree(lab_dir, ignore_errors=True)
                lab_dir = None
                item.status = "failed"
                item.error = "rendered lab not ingested (track/level missing)"
                db.commit()
                return

            # Stage the instance + pending review -- identical shape to the
            # manual reskin path so the review pane and the spawn-time env
            # injection read it correctly.
            override_blob = {
                "cosmetic": result.get("cosmetic_values", {}),
                "env": result.get("env_overrides", {}),
                "flag": result.get("flag"),
                "lab_name": item.title or (result.get("lab_yaml", {}) or {}).get("name"),
                "lab_slug": result.get("lab_slug"),
            }
            instance = TemplateInstance(
                template_id=template_row.id,
                template_version=result.get("template_version", 1),
                course_id=job.course_id,
                instructor_id=job.instructor_id,
                fork_type="cosmetic",
                override_values=json.dumps(override_blob),
                lab_id=lab_id,
                status="staged",
            )
            db.add(instance)
            db.flush()
            pr = StudioPendingReview(
                instance_id=instance.id,
                instructor_id=job.instructor_id,
                course_id=job.course_id,
                fork_type="cosmetic",
                tier="parameterize",
                lint_status=gate.get("lint_status"),
                security_scan_status=gate.get("security_scan_status"),
                tester_status=gate.get("tester_status"),
                lint_report=json.dumps(gate.get("lint_report", {})),
                approval_status="pending",
            )
            db.add(pr)
            db.flush()
            item.instance_id = instance.id
            item.pending_review_id = pr.id
            item.lab_id = lab_id
            item.status = "ready"
            item.stage = "done"
            item.claimed_by = None
            item.lease_until = None
            job.token_cost = (job.token_cost or 0) + (tokens or 0)
            db.commit()
            lab_dir = None  # committed: keep the rendered dir
            logger.info("gen item %s ready (lab_id=%s)", item_id, lab_id)
        except Exception as e:
            db.rollback()
            logger.warning("gen item %s build failed: %s", item_id, e)
            it2 = db.get(ExerciseGenItem, item_id)
            if it2:
                it2.status = "failed"
                it2.error = str(e)[:300]
                it2.claimed_by = None
                it2.lease_until = None
                db.commit()
    finally:
        if lab_dir:
            shutil.rmtree(lab_dir, ignore_errors=True)
        db.close()


def _advance_building_jobs():
    """Flip a building job to awaiting_review once no items are pending/building."""
    from app.models import ExerciseGenJob, ExerciseGenItem
    db = SessionLocal()
    try:
        jobs = db.query(ExerciseGenJob).filter(ExerciseGenJob.status == "building").all()
        for job in jobs:
            unfinished = (
                db.query(ExerciseGenItem)
                .filter(ExerciseGenItem.job_id == job.id)
                .filter(ExerciseGenItem.status.in_(("pending", "building")))
                .count()
            )
            if unfinished == 0:
                job.status = "awaiting_review"
                db.commit()
                logger.info("gen job %s -> awaiting_review", job.id)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# The tick (registered in start_scheduler)
# ---------------------------------------------------------------------------

async def tick_generation_jobs():
    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            # 1) plan one job, if any
            db = SessionLocal()
            try:
                jid = _claim_planning_job(db)
            finally:
                db.close()
            if jid is not None:
                await loop.run_in_executor(None, _plan_job, jid)

            # 2) build one item, if any
            db = SessionLocal()
            try:
                iid = _claim_building_item(db)
            finally:
                db.close()
            if iid is not None:
                await loop.run_in_executor(None, _build_item, iid)

            # 3) advance any building jobs whose items are all terminal
            await loop.run_in_executor(None, _advance_building_jobs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("gen tick error: %s", e)
