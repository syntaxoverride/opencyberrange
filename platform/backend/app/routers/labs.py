"""
Lab management routes - spawn, stop, and manage lab sessions
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging
import os
import json
import yaml


def _prebuild_progress():
    """Read the background lab-prebuild progress file (written by
    prebuild-labs.sh into the labs dir). None when there is no prebuild in
    flight or it finished long ago."""
    path = os.path.join(os.environ.get("LABS_DIR", "/labs"), ".prebuild-progress.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

from app.database import get_db
from app.auth import get_current_active_user, is_impersonating
from app.models import User, Lab, LabSession, WireGuardConfig
from app.services.docker_manager import DockerManager, get_subnet_id, RangeBoxCapacityError
from app.services.wireguard_manager import WireGuardManager
from app.config import settings
from app.crypto import encrypt_private_key, decrypt_private_key, is_encrypted
from app.services.activity import log_activity, EventTypes
from app.services import settings_service


def get_vpn_client_ip(user_id: int, base: str = "10.0.0") -> str:
    """
    Calculate a unique VPN client IP from user_id.

    Supports both 3-octet bases (e.g. "10.0.0" -> 10.0.0.{host}, /24, 244 users)
    and 2-octet bases (e.g. "10.0" -> 10.0.{third}.{host}, /16, ~62k users).

    Avoids .0 (network), .1 (gateway/server), and .255 (broadcast) in the
    host octet by mapping into the 10-254 range (245 usable per /24 slice).
    """
    base_parts = base.split(".")
    usable_per_slice = 245  # 10..254 inclusive
    idx = user_id - 1       # 0-based

    if len(base_parts) >= 3:
        # 3-octet base (e.g. "10.0.0"): single /24 subnet, host = 10..254
        host = (idx % usable_per_slice) + 10
        return f"{base}.{host}"
    else:
        # 2-octet base (e.g. "10.0"): /16 range with multiple /24 slices
        third_octet = (idx // usable_per_slice) % 255
        fourth_octet = (idx % usable_per_slice) + 10
        return f"{base}.{third_octet}.{fourth_octet}"


def _acquire_vpn_allocator_lock(db: Session) -> None:
    """Serialize VPN IP allocation across uvicorn workers.

    Takes a transaction-scoped Postgres advisory lock, released automatically
    at commit or rollback, so only one worker at a time can run the
    read-probe-insert sequence. Non-Postgres engines (unit tests on SQLite)
    skip the lock and rely on the unique constraint plus retry as the backstop.
    """
    try:
        if db.get_bind().dialect.name == "postgresql":
            from sqlalchemy import text
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext('wireguard_client_ip_alloc'))"))
    except Exception as e:
        logger.warning(f"VPN allocator advisory lock unavailable, relying on unique constraint: {e}")


def allocate_vpn_client_ip(db: Session, user_id: int, base: str = "10.0.0") -> str:
    """Pick a collision-free VPN client IP for a user.

    The deterministic mapping in get_vpn_client_ip is tried first so a user keeps
    a stable address. The mapping wraps once the address space fills, so two
    users can land on the same address; when the first choice is already held by
    another peer, probe forward through the same scheme for the next free one.
    """
    taken = {
        ip for (ip,) in db.query(WireGuardConfig.client_ip)
        .filter(WireGuardConfig.user_id != user_id).all()
        if ip
    }
    span = 245 if len(base.split(".")) >= 3 else 245 * 255
    for offset in range(span):
        candidate = get_vpn_client_ip(user_id + offset, base)
        if candidate not in taken:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
        detail="VPN address pool exhausted; contact an administrator."
    )


logger = logging.getLogger(__name__)
router = APIRouter()

docker_manager = DockerManager()
wireguard_manager = WireGuardManager(
    api_url=settings.WG_API_URL,
    api_key=settings.WG_API_KEY
)


@router.get("/")
async def get_labs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get available labs"""
    labs = db.query(Lab).filter(Lab.is_active == True).all()
    return {"labs": [{"id": l.id, "name": l.name, "slug": l.slug} for l in labs]}


@router.post("/spawn/{lab_slug}")
async def spawn_lab(
    lab_slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Spawn a lab environment for the user"""

    # Check if user already has an active session
    existing_session = db.query(LabSession).filter(
        LabSession.user_id == current_user.id,
        LabSession.status.in_(["starting", "running"])
    ).first()

    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active lab session. Please stop it first."
        )

    # Find the lab
    lab = db.query(Lab).filter(Lab.slug == lab_slug).first()
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab '{lab_slug}' not found"
        )

    # Still preparing? When the installer pre-builds lab images in the
    # background (so the admin gets in fast), a container lab whose image is not
    # built yet cannot spawn. Return a clear "preparing" message instead of a
    # cryptic image-not-found failure. services:{} labs (no image) are never gated.
    _prog = _prebuild_progress()
    if _prog and not _prog.get("complete", True):
        try:
            _comp = yaml.safe_load(lab.compose_file or "") or {}
        except Exception:
            _comp = {}
        if _comp.get("services") and lab_slug not in (_prog.get("done") or []):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exercise is still being prepared (its environment is "
                       "building in the background). Try again in a few minutes.")

    # Shared-VM labs need /dev/kvm on the host; refuse to spawn a lab whose
    # Windows target cannot exist rather than hand out a broken session
    if getattr(lab, 'requires_kvm', False):
        from app.services.docker_manager import host_kvm_available
        if not host_kvm_available():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This exercise uses a shared Windows VM, which needs KVM "
                    "hardware virtualization. This server has no /dev/kvm, so "
                    "the exercise is unavailable here."
                )
            )

    # Check if RangeBox was requested (default: true for browser-based desktop)
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    rangebox_enabled = body.get("rangebox", False)
    rangebox_image = body.get("rangebox_image", None)  # "kali" or "ubuntu"
    # Backward compatibility: clients that pass {"wait": true} get the old
    # blocking behavior where the response arrives once the lab is up.
    wait_for_ready = bool(body.get("wait", False))

    # Session length comes from the operator-tunable setting (was hardcoded 2h)
    try:
        session_hours = int(settings_service.get_setting(db, "default_session_hours", "2"))
    except (TypeError, ValueError):
        session_hours = 2

    # Create session record
    is_diagnostic = current_user.diagnostic_until and current_user.diagnostic_until > datetime.now(timezone.utc).replace(tzinfo=None)
    session = LabSession(
        user_id=current_user.id,
        lab_id=lab.id,
        status="starting",
        is_diagnostic=bool(is_diagnostic),
        rangebox_enabled=bool(rangebox_enabled),
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=session_hours)
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Capture everything the background bring-up needs now. The Request object
    # and the request-scoped DB session are not safe to touch after the
    # response is returned, so the task reloads the session row in its own
    # SessionLocal and works from plain captured values.
    import asyncio
    from app.database import SessionLocal

    loop = asyncio.get_event_loop()
    session_id = session.id
    user_id = current_user.id
    lab_id = lab.id
    lab_name = lab.name
    compose_content = lab.compose_file or ""
    diagnostic = bool(is_diagnostic)
    req_client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else None)

    async def bring_up_lab():
        """Bring up the lab environment and record the outcome on the session row.

        Runs the blocking docker compose work in the default thread pool so the
        event loop stays free. All progress lands in lab_sessions.status
        (starting -> running or error), which any worker can read, so the
        frontend polls GET /spawn-status/{session_id} regardless of which
        uvicorn worker handled the spawn.
        """
        bg_db = SessionLocal()
        try:
            bg_session = bg_db.query(LabSession).filter(LabSession.id == session_id).first()
            if not bg_session:
                logger.warning(f"Session {session_id} not found during background spawn of {lab_slug}")
                return

            try:
                # All labs (with or without services) go through create_lab_environment.
                # It creates ONE network per user+lab and connects both the lab's own
                # Docker services AND any x-ocr-shared-containers to it.
                result = await loop.run_in_executor(
                    None,
                    lambda: docker_manager.create_lab_environment(
                        user_id=user_id,
                        lab_slug=lab_slug,
                        compose_content=compose_content,
                    ),
                )

                bg_session.network_id = result.get("network_id", f"lab_{user_id}_{lab_slug}")
                second_octet, third_octet = get_subnet_id(user_id, lab_slug)
                bg_session.network_subnet = result.get("subnet", f"10.{second_octet}.{third_octet}.0/24")

                # Spawn RangeBox container if requested (also in thread pool)
                rangebox_spawned = False
                if rangebox_enabled:
                    network_name = f"lab_{user_id}_{lab_slug}"
                    try:
                        rangebox_id = await loop.run_in_executor(
                            None,
                            lambda: docker_manager.spawn_rangebox(
                                user_id=user_id,
                                lab_slug=lab_slug,
                                network_name=network_name,
                                image=rangebox_image,
                            )
                        )
                    except RangeBoxCapacityError as e:
                        # Lab itself is up, so only RangeBox gets disabled
                        logger.warning(f"RangeBox capacity reached for lab {lab_slug}: {e}")
                        rangebox_id = None
                    rangebox_spawned = rangebox_id is not None
                    if not rangebox_spawned:
                        logger.warning(f"RangeBox failed to spawn for lab {lab_slug}, continuing without it")
                        bg_session.rangebox_enabled = False

                bg_session.status = "running"
                bg_db.commit()

                logger.info(f"Lab {lab_slug} spawned for user {user_id} (rangebox={rangebox_spawned})")

                log_activity(bg_db, EventTypes.LAB_STARTED,
                              actor_id=user_id, target_type="lab",
                              target_id=lab_id, target_label=lab_name,
                              detail={"source": "diagnostic", "rangebox": rangebox_spawned} if diagnostic else {"rangebox": rangebox_spawned},
                              ip_address=req_client_ip)

            except Exception as e:
                logger.error(f"Failed to spawn lab {lab_slug}: {e}", exc_info=True)
                # Tear down whatever partially came up so no orphaned network or
                # containers block the user's next spawn attempt.
                try:
                    await loop.run_in_executor(
                        None, docker_manager.destroy_lab_environment, user_id, lab_slug,
                    )
                except Exception as teardown_err:
                    logger.warning(f"Teardown after failed spawn of {lab_slug} was incomplete: {teardown_err}")
                try:
                    bg_db.rollback()
                    bg_session = bg_db.query(LabSession).filter(LabSession.id == session_id).first()
                    if bg_session:
                        bg_session.status = "error"
                        bg_db.commit()
                except Exception:
                    pass
        finally:
            bg_db.close()

    if wait_for_ready:
        # Legacy blocking path: hold the request open until the lab is up
        await bring_up_lab()
        db.refresh(session)
        if session.status != "running":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start lab environment. Please try again or contact an administrator."
            )
        return {
            "message": "Lab environment started",
            "session_id": session.id,
            "lab_slug": lab_slug,
            "status": session.status,
            "network_id": session.network_id,
            "network_subnet": session.network_subnet,
            "rangebox_enabled": session.rangebox_enabled,
            "expires_at": session.expires_at.isoformat() + "Z" if session.expires_at else None
        }

    # Default path: kick the bring-up off in the background and return at once.
    # The frontend polls GET /api/labs/spawn-status/{session_id} until the
    # status field leaves "starting".
    asyncio.create_task(bring_up_lab())

    return {
        "message": "Lab environment starting",
        "session_id": session.id,
        "lab_slug": lab_slug,
        "status": "starting",
        "rangebox_enabled": session.rangebox_enabled,
        "expires_at": session.expires_at.isoformat() + "Z" if session.expires_at else None,
        "status_url": f"/api/labs/spawn-status/{session.id}"
    }


@router.get("/spawn-status/{session_id}")
async def get_spawn_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Poll the spawn progress of a lab session.

    The status field moves starting -> running on success or starting -> error
    on failure. Status lives on the lab_sessions row, so the answer is correct
    no matter which worker ran the background bring-up.
    """
    session = db.query(LabSession).filter(LabSession.id == session_id).first()
    is_privileged = current_user.role in ("admin", "instructor")
    if not session or (session.user_id != current_user.id and not is_privileged):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab session not found"
        )

    lab = db.query(Lab).filter(Lab.id == session.lab_id).first()

    return {
        "session_id": session.id,
        "lab_id": session.lab_id,
        "lab_slug": lab.slug if lab else None,
        "status": session.status,
        "network_id": session.network_id,
        "network_subnet": session.network_subnet,
        "rangebox_enabled": session.rangebox_enabled,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "expires_at": (session.expires_at.isoformat() + "Z") if session.expires_at else None
    }


@router.get("/prebuild-status")
async def prebuild_status(current_user: User = Depends(get_current_active_user)):
    """Background lab-prebuild progress for the 'still preparing' banner."""
    prog = _prebuild_progress()
    if not prog:
        return {"active": False}
    return {
        "active": not prog.get("complete", True),
        "total": prog.get("total", 0),
        "done": prog.get("done_count", 0),
        "building": prog.get("building", ""),
    }


@router.post("/stop")
async def stop_lab(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Stop the user's active lab session"""
    
    # Find active session
    session = db.query(LabSession).filter(
        LabSession.user_id == current_user.id,
        LabSession.status.in_(["starting", "running"])
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active lab session found"
        )
    
    lab = db.query(Lab).filter(Lab.id == session.lab_id).first()
    lab_slug = lab.slug if lab else "unknown"
    
    # Mark as stopping immediately to prevent duplicate stop requests
    session.status = "stopping"
    db.commit()
    db.refresh(session)
    
    # Run cleanup in background to avoid blocking
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.database import SessionLocal

    uses_shared = False

    async def cleanup_lab():
        # Create new database session for background task
        bg_db = SessionLocal()
        try:
            # Reload session in new DB context
            bg_session = bg_db.query(LabSession).filter(LabSession.id == session.id).first()
            if not bg_session:
                logger.warning(f"Session {session.id} not found in background cleanup")
                return

            # Run the blocking Docker cleanup in a thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                if uses_shared:
                    # Partial teardown: keep the bridge network intact
                    await loop.run_in_executor(
                        executor,
                        docker_manager.cleanup_exercise_containers,
                        current_user.id,
                        lab_slug
                    )
                else:
                    # Non-shared lab: full teardown
                    await loop.run_in_executor(
                        executor,
                        docker_manager.destroy_lab_environment,
                        current_user.id,
                        lab_slug
                    )

            # Update session status after cleanup
            bg_session.status = "stopped"
            bg_db.commit()
            logger.info(f"Lab {lab_slug} stopped for user {current_user.id} (shared={uses_shared})")
        except Exception as e:
            logger.error(f"Failed to stop lab {lab_slug}: {e}")
            # Still mark as stopped even if cleanup failed
            try:
                bg_session = bg_db.query(LabSession).filter(LabSession.id == session.id).first()
                if bg_session:
                    bg_session.status = "stopped"
                    bg_db.commit()
            except Exception:
                pass
        finally:
            bg_db.close()

    # Start cleanup in background (fire and forget)
    asyncio.create_task(cleanup_lab())

    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host if request.client else None
    is_diagnostic = current_user.diagnostic_until and current_user.diagnostic_until > datetime.now(timezone.utc).replace(tzinfo=None)
    log_activity(db, EventTypes.LAB_STOPPED,
                  actor_id=current_user.id, target_type="lab",
                  target_id=session.lab_id, target_label=lab_slug,
                  detail={"source": "diagnostic"} if is_diagnostic else None,
                  ip_address=client_ip)

    # Return immediately
    return {"message": "Lab stop initiated. Cleanup in progress."}


@router.post("/extend")
async def extend_lab_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Extend the user's active lab session by 1 hour"""
    
    # Find active session
    session = db.query(LabSession).filter(
        LabSession.user_id == current_user.id,
        LabSession.status == "running"
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active lab session found"
        )
    
    # Extend by 1 hour
    if session.expires_at:
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        session.expires_at = expires_at + timedelta(hours=1)
    else:
        session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    db.commit()
    
    logger.info(f"Extended lab session {session.id} for user {current_user.id}")
    
    return {
        "message": "Session extended by 1 hour",
        "expires_at": session.expires_at.isoformat() + "Z" if session.expires_at else None
    }


@router.get("/active")
async def get_active_lab(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the user's active lab session"""
    
    session = db.query(LabSession).filter(
        LabSession.user_id == current_user.id,
        LabSession.status == "running"
    ).first()
    
    if not session:
        return {"active_session": None}
    
    lab = db.query(Lab).filter(Lab.id == session.lab_id).first()
    
    return {
        "active_session": {
            "id": session.id,
            "lab_id": session.lab_id,
            "lab_slug": lab.slug if lab else None,
            "lab_name": lab.name if lab else None,
            "status": session.status,
            "network_id": session.network_id,
            "network_subnet": session.network_subnet,
            "rangebox_enabled": session.rangebox_enabled,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "expires_at": (session.expires_at.isoformat() + "Z") if session.expires_at else None
        }
    }


# ==================== VPN Configuration ====================

def vpn_is_enabled(db: Session) -> bool:
    """Whether VPN access is turned on for the platform (Admin > Settings > VPN).

    Read uncached: this gates handing out a working VPN credential, and the
    settings cache is per worker, so a cached read would keep serving configs on
    most workers for up to the cache TTL after an admin switched VPN off.

    Defaults to on so an install that predates the setting keeps working.
    """
    raw = settings_service.get_setting_fresh(db, "vpn_enabled", "true") or "true"
    return raw.strip().lower() in ("true", "1", "yes")


@router.get("/vpn-config", response_class=PlainTextResponse)
async def get_vpn_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get or generate WireGuard VPN configuration - routes ALL lab networks"""
    # An admin who turns VPN off expects it off, so refuse here rather than only
    # hiding the button: this endpoint provisions a real peer and hands back a
    # working credential, and it is reachable directly.
    if not vpn_is_enabled(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="VPN access is disabled on this platform. Use the RangeBox to reach your labs from the browser.",
        )
    imp = is_impersonating(current_user)
    wg_config = db.query(WireGuardConfig).filter(
        WireGuardConfig.user_id == current_user.id
    ).first()

    if not wg_config:
        # Read-only "View As": this GET has side effects (keypair + live peer),
        # which the verb-based impersonation middleware does not catch. Refuse to
        # provision on the student's behalf while impersonating.
        if imp:
            raise HTTPException(status_code=403, detail="Read-only: cannot provision a VPN config while viewing as another user")
        # Generate new keypair and config
        private_key, public_key = wireguard_manager.generate_keypair()

        # Encrypt private key before storing if encryption is configured
        stored_private_key = private_key
        try:
            if settings.WG_ENCRYPTION_KEY:
                stored_private_key = encrypt_private_key(private_key)
                logger.debug(f"Encrypted WireGuard private key for user {current_user.id}")
        except Exception as e:
            logger.warning(f"WireGuard key encryption not available: {e}")

        # Race-safe allocation: the check-then-insert below runs on many
        # workers at once, so two users could otherwise be handed the same
        # client_ip. Defense is layered: a Postgres advisory lock serializes
        # the whole probe+insert, and the unique constraints on client_ip and
        # user_id turn any remaining race into an IntegrityError that gets
        # retried with a fresh probe.
        from sqlalchemy.exc import IntegrityError
        max_alloc_attempts = 5
        for attempt in range(max_alloc_attempts):
            _acquire_vpn_allocator_lock(db)
            client_ip = allocate_vpn_client_ip(db, current_user.id, settings.WG_CLIENT_BASE)
            wg_config = WireGuardConfig(
                user_id=current_user.id,
                private_key=stored_private_key,
                public_key=public_key,
                client_ip=client_ip
            )
            db.add(wg_config)
            try:
                db.commit()
                break
            except IntegrityError:
                db.rollback()
                # Either another worker took this client_ip, or a concurrent
                # request already created THIS user's config (user_id is
                # unique too). Reuse the existing row when present, otherwise
                # probe again for a free address.
                wg_config = db.query(WireGuardConfig).filter(
                    WireGuardConfig.user_id == current_user.id
                ).first()
                if wg_config:
                    break
                logger.warning(
                    f"VPN client_ip {client_ip} lost to a concurrent allocation "
                    f"(attempt {attempt + 1}/{max_alloc_attempts}), retrying"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not allocate a VPN address. Please try again."
            )
    
    # Auto-register peer with Peer Manager if not already registered (skip while
    # impersonating: read-only View As must not register a peer for the student).
    if not current_user.vpn_registered and not imp:
        try:
            success = wireguard_manager.sync_peer(wg_config.public_key, wg_config.client_ip)
            if success:
                current_user.vpn_registered = True
                db.commit()
                logger.info(f"Auto-registered VPN peer for user {current_user.username}")
        except Exception as e:
            logger.error(f"Failed to auto-register VPN peer: {e}")
            # Don't fail the request - user can still get config, admin can sync later
    
    # Decrypt private key if it's encrypted
    private_key_for_config = wg_config.private_key
    if is_encrypted(wg_config.private_key):
        try:
            private_key_for_config = decrypt_private_key(wg_config.private_key)
        except Exception as e:
            logger.error(f"Failed to decrypt WireGuard private key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate VPN configuration"
            )
    
    # Route lab networks (10.100/14, 10.104/13, 10.112/12, 10.128/9) through the
    # VPN tunnel. 10.128/9 covers the 10.200.x lab range.
    # 10.50.0.0/16 (standalone RangeBox pool) is intentionally NOT routed: the
    # RangeBox is browser/noVNC only (proxied via the backend), never reached
    # from a VPN peer, so pushing it would only hijack a student's home LAN if
    # they happen to use 10.50.x.x at home.
    # Prefer DB settings (editable via admin UI) over .env values
    vpn_endpoint = settings_service.get_setting(db, "vpn_endpoint") or settings.WG_SERVER_ENDPOINT
    vpn_pubkey = settings_service.get_setting(db, "vpn_public_key") or settings.WG_SERVER_PUBLIC_KEY

    # Check if WebSocket tunnel mode is enabled (for Cloudflare Tunnel deployments)
    wstunnel_enabled = settings_service.get_setting(db, "vpn_wstunnel_enabled", "false").lower() == "true"
    wstunnel_url = settings_service.get_setting(db, "vpn_wstunnel_url", "") if wstunnel_enabled else None

    # Derive platform base URL for self-hosted binary downloads
    # Uses the Host header from the request (e.g. "labs.attackanddefend.com")
    # Always use HTTPS — real deployments sit behind Cloudflare/TLS termination
    platform_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    platform_base_url = f"https://{platform_host}" if platform_host else None

    config_content = wireguard_manager.generate_client_config(
        private_key=private_key_for_config,
        client_ip=wg_config.client_ip,
        server_public_key=vpn_pubkey,
        server_endpoint=vpn_endpoint,
        allowed_ips="10.100.0.0/14,10.104.0.0/13,10.112.0.0/12,10.128.0.0/9",
        wstunnel_url=wstunnel_url if wstunnel_url else None,
        platform_base_url=platform_base_url
    )

    log_activity(db, EventTypes.VPN_DOWNLOADED,
                  actor_id=current_user.id, target_type="user",
                  target_id=current_user.id, target_label=current_user.username)

    return config_content


@router.get("/vpn-status")
async def get_vpn_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get VPN registration status for current user - checks Peer Manager directly"""
    # Carries the platform-wide VPN switch to the student UI. The settings API is
    # admin-only, so this is where a student's dashboard learns VPN is turned off
    # and stops offering a config it would be refused.
    enabled = vpn_is_enabled(db)

    wg_config = db.query(WireGuardConfig).filter(
        WireGuardConfig.user_id == current_user.id
    ).first()

    if not wg_config:
        return {
            "enabled": enabled,
            "has_config": False,
            "vpn_registered": False,
            "client_ip": None
        }
    
    # Check Peer Manager directly to see if peer is registered and connected
    actually_registered = False
    actually_connected = False
    if wg_config.public_key:
        try:
            actually_registered = wireguard_manager.peer_exists(wg_config.public_key)
            
            # Check if peer is actively connected (has recent handshake)
            if actually_registered:
                actually_connected = wireguard_manager.is_peer_connected(wg_config.public_key)
            
            # Sync database flag if it's out of sync
            if actually_registered != current_user.vpn_registered:
                current_user.vpn_registered = actually_registered
                db.commit()
                logger.info(f"Synced VPN registration status for user {current_user.username}: {actually_registered}")
        except Exception as e:
            logger.warning(f"Could not verify peer status with Peer Manager: {e}")
            # Fall back to database flag if Peer Manager check fails
            actually_registered = current_user.vpn_registered
            actually_connected = False
    
    return {
        "enabled": enabled,
        "has_config": True,
        "vpn_registered": actually_registered,
        "vpn_connected": actually_connected,  # New field for actual connection status
        "client_ip": wg_config.client_ip
    }






def get_track_for_lab(db: Session, lab: Lab):
    """Get the track_id for a lab via lab.level.track. Returns None if unavailable."""
    if not lab or not lab.level_id:
        return None
    from app.models import Level, Track
    level = db.query(Level).filter(Level.id == lab.level_id).first()
    if level and level.track_id:
        return level.track_id
    return None




















