"""
Background task scheduler
Handles periodic cleanup tasks like terminating expired lab sessions
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import LabSession
from app.services.docker_manager import DockerManager
from app import modules as module_registry

logger = logging.getLogger(__name__)

docker_manager = DockerManager()
_session_cleanup_task = None
_module_tasks = {}   # label -> asyncio.Task, one per discovered module tick




async def cleanup_expired_sessions():
    """
    Background task that checks for expired lab sessions and stops them.
    Runs every 2 minutes.
    """
    while True:
        try:
            await asyncio.sleep(120)  # Wait 2 minutes
            
            db: Session = SessionLocal()
            try:
                now = datetime.now(timezone.utc)
                
                # Find all running sessions that have expired
                sessions = db.query(LabSession).filter(
                    LabSession.status == "running",
                    LabSession.expires_at < now
                ).all()
                
                stopped_count = 0
                
                for session in sessions:
                    try:
                        # Get the lab slug
                        lab = session.lab
                        if lab:
                            # Stop the full lab environment
                            docker_manager.destroy_lab_environment(session.user_id, lab.slug)
                            logger.info(f"Stopped expired lab environment for user {session.user_id}, lab {lab.slug}")
                        
                        # Update session status
                        session.status = "expired"
                        session.stopped_at = now
                        db.commit()
                        stopped_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to stop expired session {session.id}: {e}")
                        db.rollback()
                        # Still mark as expired even if cleanup failed
                        try:
                            session.status = "expired"
                            session.stopped_at = now
                            db.commit()
                        except Exception:
                            db.rollback()
                
                if stopped_count > 0:
                    logger.info(f"Cleanup: Stopped {stopped_count} expired lab sessions")

                # --- Cleanup stale 'starting' sessions (stuck > 5 min) ---
                stale_cutoff = now - timedelta(minutes=5)
                stale_sessions = db.query(LabSession).filter(
                    LabSession.status == "starting",
                    LabSession.started_at < stale_cutoff
                ).all()

                for session in stale_sessions:
                    try:
                        lab = session.lab
                        if lab:
                            try:
                                docker_manager.destroy_lab_environment(session.user_id, lab.slug)
                            except Exception:
                                pass
                        session.status = "error"
                        session.stopped_at = now
                        db.commit()
                        logger.warning(f"Cleanup: Marked stale starting session {session.id} (user {session.user_id}) as error")
                    except Exception as e:
                        logger.error(f"Failed to clean up stale session {session.id}: {e}")
                        db.rollback()

                # --- Cleanup expired standalone RangeBox containers ---
                try:
                    standalone_stopped = 0
                    containers = docker_manager.client.containers.list(
                        filters={"label": "ocr.role=rangebox-standalone"}
                    ) if docker_manager.client else []

                    for c in containers:
                        expires_str = c.labels.get("ocr.expires_at", "")
                        if not expires_str:
                            continue
                        try:
                            expires_at = datetime.fromisoformat(expires_str)
                            if expires_at.tzinfo is None:
                                expires_at = expires_at.replace(tzinfo=timezone.utc)
                            if expires_at < now:
                                user_id_str = c.labels.get("ocr.user_id", "?")
                                logger.info(f"Destroying expired standalone RangeBox for user {user_id_str}")
                                c.remove(force=True)
                                standalone_stopped += 1
                                # Clean up the per-user standalone network
                                try:
                                    uid = int(user_id_str)
                                    docker_manager.destroy_standalone_rangebox(uid)
                                except (ValueError, Exception) as ne:
                                    logger.debug(f"Could not clean up standalone network for user {user_id_str}: {ne}")
                        except Exception as e:
                            logger.warning(f"Error parsing expiry for standalone RangeBox {c.name}: {e}")

                    if standalone_stopped > 0:
                        logger.info(f"Cleanup: Removed {standalone_stopped} expired standalone RangeBox containers")
                except Exception as e:
                    logger.warning(f"Error cleaning up standalone RangeBoxes: {e}")


            except Exception as e:
                logger.error(f"Error in session cleanup task: {e}")
            finally:
                db.close()
                
        except asyncio.CancelledError:
            logger.info("Session cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in session cleanup task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


def start_scheduler():
    """Start the background scheduler tasks"""
    global _session_cleanup_task

    logger.info("Starting background scheduler...")

    # Start expired session cleanup task
    if _session_cleanup_task is None or _session_cleanup_task.done():
        _session_cleanup_task = asyncio.create_task(cleanup_expired_sessions())
        logger.info("Started expired session cleanup task")

    # Start each present module's background tick. Editions with no
    # optional modules installed have none to start.
    # Adding a module with a scheduler_tick needs no edit to this file.
    for label, tick in module_registry.scheduler_ticks():
        existing = _module_tasks.get(label)
        if existing is None or existing.done():
            _module_tasks[label] = asyncio.create_task(tick())
            logger.info("Started module tick: %s", label)


def shutdown_scheduler():
    """Stop all background scheduler tasks"""
    global _session_cleanup_task

    logger.info("Shutting down background scheduler...")

    tasks = []
    if _session_cleanup_task and not _session_cleanup_task.done():
        tasks.append(_session_cleanup_task)
    tasks.extend(t for t in _module_tasks.values() if t and not t.done())

    for t in tasks:
        t.cancel()
        try:
            asyncio.get_event_loop().run_until_complete(t)
        except asyncio.CancelledError:
            pass

    _session_cleanup_task = None
    _module_tasks.clear()
