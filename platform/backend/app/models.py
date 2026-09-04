"""
Database models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Index, UniqueConstraint, CheckConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    student_id = Column(String(20), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Kept for backward compat; derived from role
    role = Column(String(20), default="student", nullable=False)  # student | instructor | admin
    is_approved = Column(Boolean, default=False)

    # Account locking
    is_locked = Column(Boolean, default=False)
    failed_attempts = Column(Integer, default=0)
    locked_at = Column(DateTime, nullable=True)

    # VPN registration status
    vpn_registered = Column(Boolean, default=False)

    # Force password change on next login
    must_change_password = Column(Boolean, default=False, nullable=True)

    # Diagnostic mode: activity events before this timestamp are tagged as diagnostic
    diagnostic_until = Column(DateTime, nullable=True)

    # MFA (TOTP). totp_secret stays null until the user enrolls; sized for an
    # encrypted-at-rest secret, not just the raw base32 value.
    totp_secret = Column(String(255), nullable=True)
    mfa_enabled = Column(Boolean, default=False, server_default=text("false"), nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    @property
    def is_instructor(self):
        """True if user has instructor or admin role."""
        return self.role in ('instructor', 'admin')

    # Relationships
    sessions = relationship("LabSession", back_populates="user", foreign_keys="[LabSession.user_id]")
    wireguard_config = relationship("WireGuardConfig", back_populates="user", uselist=False)
    completions = relationship("LabCompletion", back_populates="user")
    flag_attempts = relationship("FlagAttempt", back_populates="user")
    instructed_courses = relationship("Course", back_populates="instructor")
    course_enrollments = relationship("CourseEnrollment", back_populates="user")
    achievements = relationship("Achievement", back_populates="user")


class Track(Base):
    """Learning tracks (Windows, Linux, Web, Network)"""
    __tablename__ = "tracks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # Icon component name
    color = Column(String(20))  # Hex color
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    sequential = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    levels = relationship("Level", back_populates="track", order_by="Level.level_number")


class Level(Base):
    """Levels within tracks"""
    __tablename__ = "levels"
    
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    level_number = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    track = relationship("Track", back_populates="levels")
    labs = relationship("Lab", back_populates="level", order_by="Lab.sort_order")
    
    __table_args__ = (
        Index('ix_level_track_number', 'track_id', 'level_number', unique=True),
    )


class Lab(Base):
    __tablename__ = "labs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    description = Column(Text)
    scenario = Column(Text, nullable=True)  # Full narrative scenario for immersive experience
    scenario_brief = Column(Text, nullable=True)  # Short version for lab list view (optional)
    difficulty = Column(String(20), default="beginner")
    category = Column(String(50), default="general")
    objectives = Column(Text)  # JSON array stored as text
    compose_file = Column(Text, nullable=False)
    duration_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Curriculum fields
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    flag_hash = Column(String(255), nullable=True)  # SHA256 of correct flag
    hints = Column(Text, nullable=True)  # JSON array of hints
    tools = Column(Text, nullable=True)  # JSON array of tools
    hostnames = Column(Text, nullable=True)  # JSON array of hostname mappings: [{"ip_offset": "17", "hostname": "vulnerable.lab", "description": "Main web app"}]
    # Reveal per-node target IPs in the Exercise Network panel (drills / guided tours)
    show_target_ips = Column(Boolean, default=False)
    # JSON array of topology nodes [{"id","label","ip_offset",...}] used to compute target IPs
    topology_nodes = Column(Text, nullable=True)
    # Lab depends on a VM the host runs under KVM, so it needs /dev/kvm
    requires_kvm = Column(Boolean, default=False)
    # Course-exclusive: only visible to students enrolled in a course that assigns this lab
    is_course_exclusive = Column(Boolean, default=False)  # Deprecated — use visibility
    # Course-available: lab is designated for course assignments
    is_course_available = Column(Boolean, default=False)  # Deprecated — use visibility
    # Lab visibility lifecycle: draft | course | pending_public | public
    visibility = Column(String(20), default="public", nullable=False)
    # Wiki page path for workbook deep-link (e.g. "CH01_Enumeration/01_Basic_Port_Scan/")
    workbook = Column(String(255), nullable=True)
    # Curriculum week number for auto-assignment grouping (e.g. week: 3 → "Week 3" assignment)
    week = Column(Integer, nullable=True)
    # Who created this lab (NULL for system-discovered labs)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Static validation results (populated by lab scanner / validate-lab.py)
    validation_status = Column(String(20), nullable=True)  # ok | warning | error
    validation_errors = Column(Text, nullable=True)  # JSON array of {name, passed, message, severity}
    validated_at = Column(DateTime, nullable=True)
    # ICS attack-coverage tags from lab.yaml ics_techniques: JSON array of
    # {tactic, technique_id, technique_name, note}. Powers the coverage matrix
    # generator and per-lab technique display.
    ics_techniques = Column(Text, nullable=True)

    # Relationships
    level = relationship("Level", back_populates="labs")
    creator = relationship("User", foreign_keys=[created_by])
    sessions = relationship("LabSession", back_populates="lab")
    completions = relationship("LabCompletion", back_populates="lab")
    flag_attempts = relationship("FlagAttempt", back_populates="lab")
    course_assignments = relationship("CourseLabAssignment", back_populates="lab")


class LabSession(Base):
    __tablename__ = "lab_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    network_id = Column(String(100))
    network_subnet = Column(String(20))
    status = Column(String(20), default="starting")  # starting, running, stopped, expired, error
    is_diagnostic = Column(Boolean, default=False)
    rangebox_enabled = Column(Boolean, default=False)
    impersonated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # admin who launched this session
    # Per-student flag support: when a lab seeds a unique flag into this
    # session's containers, the SHA256 of that flag is stored here and checked
    # before the shared labs.flag_hash. Chosen over a separate LabFlag table
    # because a session-scoped hash is the lighter change and matches the
    # existing flag_hash comparison path.
    seeded_flag_hash = Column(String(255), nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    stopped_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])
    lab = relationship("Lab", back_populates="sessions")

    __table_args__ = (
        Index('ix_labsession_status', 'status'),
        Index('ix_labsession_user_status', 'user_id', 'status'),
    )


class LabCompletion(Base):
    """Track user lab completions"""
    __tablename__ = "lab_completions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    completed_at = Column(DateTime, server_default=func.now())
    flag_submitted = Column(String(100))
    attempts = Column(Integer, default=1)
    hints_used = Column(Integer, default=0)
    time_spent_minutes = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)  # Track when user started working on lab for time-based hints
    
    # Relationships
    user = relationship("User", back_populates="completions")
    lab = relationship("Lab", back_populates="completions")
    
    __table_args__ = (
        Index('ix_completion_user_lab', 'user_id', 'lab_id', unique=True),
    )


class FlagAttempt(Base):
    """Log all flag submission attempts"""
    __tablename__ = "flag_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    flag_submitted = Column(String(100))
    is_correct = Column(Boolean, default=False)
    attempted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="flag_attempts")
    lab = relationship("Lab", back_populates="flag_attempts")
    
    __table_args__ = (
        Index('ix_attempt_user_lab_time', 'user_id', 'lab_id', 'attempted_at'),
    )


class WireGuardConfig(Base):
    __tablename__ = "wireguard_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    private_key = Column(String(256), nullable=False)  # Fernet-encrypted keys can be ~128 chars
    public_key = Column(String(100), nullable=False)
    client_ip = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="wireguard_config")


class RevokedToken(Base):
    """DB-backed JWT revocation list. A token whose jti appears here is dead
    regardless of its exp claim. Rows can be purged once revoked_at is older
    than the JWT lifetime."""
    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_revoked_tokens_user', 'user_id'),
    )


class InviteCode(Base):
    """Invite-gated registration. A code is single-use; email, when set,
    pins the code to one address."""
    __tablename__ = "invite_codes"

    code = Column(String(64), primary_key=True)
    email = Column(String(100), nullable=True)  # optional: restrict code to this address
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    used_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Course(Base):
    """A class/course offering with assigned labs and enrolled students"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(20), nullable=False)
    semester = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    invite_code = Column(String(20), unique=True, index=True, nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    wiki_slug = Column(String(50), nullable=True, index=True)
    wiki_theme_color = Column(String(30), default="blue")
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    instructor = relationship("User", back_populates="instructed_courses")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    lab_assignments = relationship("CourseLabAssignment", back_populates="course", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan", order_by="Assignment.sort_order")


class CourseEnrollment(Base):
    """Links students to courses"""
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, server_default=func.now())
    # Per-student scope token for tracks that scope AD objects per student
    # (e.g. ADPT: svc_kerb_<token>). Auto-assigned on enrollment, NULL for
    # courses whose tracks don't need scoping.
    scope_token = Column(String(4), nullable=True)
    # FERPA-safe classroom-scoreboard identity (Phase 6b): a stable per-course
    # integer assigned in a deterministic course-seeded SHUFFLE (not roster
    # order), shown privately to the student and used on the projected
    # scoreboard so names are never displayed. Assigned lazily; NULL until then.
    seat_number = Column(Integer, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="enrollments")
    user = relationship("User", back_populates="course_enrollments")

    __table_args__ = (
        Index('ix_enrollment_course_user', 'course_id', 'user_id', unique=True),
    )


class CourseLabAssignment(Base):
    """Labs assigned to a course"""
    __tablename__ = "course_lab_assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)
    display_name = Column(String(255), nullable=True)
    assigned_at = Column(DateTime, server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="lab_assignments")
    lab = relationship("Lab", back_populates="course_assignments")

    __table_args__ = (
        Index('ix_course_lab_assignment', 'course_id', 'lab_id', unique=True),
    )


class Achievement(Base):
    """Micro-credentials awarded to students within a course"""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=True)
    achievement_type = Column(String(30), nullable=False)
    awarded_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="achievements")
    course = relationship("Course", back_populates="achievements")
    lab = relationship("Lab")

    __table_args__ = (
        Index('ix_achievement_unique', 'user_id', 'course_id', 'achievement_type', 'lab_id', unique=True),
    )


class CourseCompletionReset(Base):
    """Instructor-initiated reset of a lab completion within a course.
    Does NOT delete LabCompletion — just marks it stale for this course."""
    __tablename__ = "course_completion_resets"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    reset_at = Column(DateTime, server_default=func.now())
    reset_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index('ix_course_reset_lookup', 'course_id', 'user_id', 'lab_id'),
    )


class Assignment(Base):
    """Named grouping of labs within a course, with optional due date"""
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    start_date = Column(DateTime, nullable=True)
    locked = Column(Boolean, default=False, server_default="false", nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    course = relationship("Course", back_populates="assignments")
    assignment_labs = relationship("AssignmentLab", back_populates="assignment", cascade="all, delete-orphan", order_by="AssignmentLab.sort_order")


class AssignmentLab(Base):
    """Links labs to assignments (labs must also be assigned to the course)"""
    __tablename__ = "assignment_labs"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)

    assignment = relationship("Assignment", back_populates="assignment_labs")
    lab = relationship("Lab")

    __table_args__ = (
        Index('ix_assignment_lab', 'assignment_id', 'lab_id', unique=True),
    )


class PlatformSetting(Base):
    """Key-value store for runtime-configurable platform settings.
    Replaces hardcoded .env values with web-editable configuration."""
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    category = Column(String(50), default="general")  # general, security, vpn, labs, appearance
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)  # If true, value is never returned in GET responses
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ActivityEvent(Base):
    """Polymorphic event log for dashboard feeds and analytics."""
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_type = Column(String(30), nullable=True)
    target_id = Column(Integer, nullable=True)
    target_label = Column(String(200), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    actor = relationship("User", foreign_keys=[actor_id])


class ExerciseTestResult(Base):
    """Persisted exercise-test result — one row per lab_slug (latest replaces older)."""
    __tablename__ = "exercise_test_results"

    id = Column(Integer, primary_key=True, index=True)
    lab_slug = Column(String(100), unique=True, nullable=False, index=True)
    lab_name = Column(String(200), nullable=False)
    track = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False)          # ok | warning | error | cancelled
    duration_seconds = Column(Float, nullable=True)
    tested_at = Column(DateTime, server_default=func.now())
    tested_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(String(20), nullable=True)
    sections_json = Column(Text, nullable=True)           # JSON array of section objects

    tested_by = relationship("User", foreign_keys=[tested_by_id])










# ============================================================================
# Exercise Studio (Phase 0): template data layer
#
# Three additive tables back the Exercise Studio:
#   exercise_templates    -- reusable, vetted lab masters (structural + cosmetic)
#   template_instances    -- an instructor's cosmetic reskin of a template
#   studio_pending_review -- the admin approval queue before student exposure
#
# All manifest/override blobs are stored as Text-encoded JSON to match the
# existing codebase convention (see Lab.objectives, Lab.hints, etc.). None of
# these tables alter the behaviour of any existing table; labs that do not
# come from a template are untouched.
# ============================================================================


class ExerciseTemplate(Base):
    """A reusable, vetted lab template that can be instantiated and reskinned.

    Covers ephemeral (Linux/Network/Web container labs)
    (Windows AD) classes. The structural manifest is locked on a cosmetic
    instantiate; only the cosmetic_schema fields can be overridden.
    """
    __tablename__ = "exercise_templates"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    klass = Column(String(20), nullable=False)        # ephemeral
    archetype = Column(String(50), nullable=False)    # linux | network | web | windows
    description = Column(Text, nullable=True)

    # Structural metadata (locked on cosmetic instantiate). JSON encoded as Text.
    structural_manifest = Column(Text, nullable=False)  # {ip_offsets, exploit_path, tester_spec, topology, ...}
    cosmetic_schema = Column(Text, nullable=False)      # {company, persona, hostname, scenario, ...} with defaults
    env_contract = Column(Text, nullable=False)         # {FLAG, CRED_<role>_USER, CRED_<role>_PASS, *_OFFSET}

    # Provenance
    source_lab_slug = Column(String(150), nullable=True)  # which existing lab this was seeded from
    latest_version = Column(Integer, default=1)
    status = Column(String(20), default="draft", nullable=False)  # draft | published | deprecated

    # Lifecycle
    tags = Column(Text, nullable=True)  # JSON array of strings
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    instances = relationship("TemplateInstance", back_populates="template")

    __table_args__ = (
        Index("ix_template_status_created", "status", "created_at"),
        CheckConstraint("status IN ('draft', 'published', 'deprecated')", name="ck_template_status"),
        CheckConstraint("klass IN ('ephemeral')", name="ck_template_klass"),
        CheckConstraint("archetype IN ('linux', 'network', 'web', 'windows')", name="ck_template_archetype"),
    )


class TemplateInstance(Base):
    """An instance of a template: instantiated by an instructor with cosmetic
    overrides, optionally materialized as a draft Lab row once approved.

    For Phase 0 only fork_type='cosmetic' is produced. The override_values JSON
    holds the reskin (company, scenario, hostname, credentials, flag) and is the
    source for per-instance FLAG/CRED_* env injection at spawn time.
    """
    __tablename__ = "template_instances"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("exercise_templates.id"), nullable=False)
    template_version = Column(Integer, nullable=False)  # which template version was cloned
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # nullable for standalone
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # cosmetic: only cosmetic_schema overrides, structure locked (Phase 0)
    # exposed: unlocked some structure but not the core (Phase 2+)
    # full_fork: changed structural_manifest, requires security scan (Phase 2+)
    fork_type = Column(String(20), nullable=False)

    # Cosmetic overrides (instructor's reskin). JSON encoded as Text.
    override_values = Column(Text, nullable=True)  # {company, scenario, hostname, credentials, flag, ...}

    # Fork provenance (for 3-way merge and patch notifications, Phase 1+)
    base_snapshot = Column(Text, nullable=True)  # structural_manifest + cosmetic_schema at fork time

    # Materialized Lab row (populated on approval; visibility='draft')
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="SET NULL"), nullable=True, unique=True)

    # Lifecycle
    status = Column(String(20), default="draft", nullable=False)  # draft | staged | published | rejected
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    template = relationship("ExerciseTemplate", back_populates="instances")
    course = relationship("Course", foreign_keys=[course_id])
    instructor = relationship("User", foreign_keys=[instructor_id])
    lab = relationship("Lab", foreign_keys=[lab_id], uselist=False)

    __table_args__ = (
        Index("ix_instance_template_instructor", "template_id", "instructor_id"),
        Index("ix_instance_course_status", "course_id", "status"),
        Index("ix_instance_lab_id", "lab_id"),
        CheckConstraint("fork_type IN ('cosmetic', 'exposed', 'full_fork')", name="ck_instance_fork_type"),
        CheckConstraint("status IN ('draft', 'staged', 'published', 'rejected')", name="ck_instance_status"),
    )


class StudioPendingReview(Base):
    """Admin approval queue: tracks staged instances awaiting human sign-off
    before they are ingested as Labs with visibility='draft'.
    """
    __tablename__ = "studio_pending_review"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("template_instances.id"), nullable=False, unique=True)
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    # What changed (mirrors the instance) and how rigorous review should be
    fork_type = Column(String(20), nullable=False)  # cosmetic | exposed | full_fork
    tier = Column(String(20), nullable=False)       # parameterize | remix | author

    # Gate stage results (from the publish pipeline)
    lint_status = Column(String(20), nullable=True)           # pass | warn | fail
    security_scan_status = Column(String(20), nullable=True)  # pass | warn | fail | not_required
    tester_status = Column(String(20), nullable=True)         # pass | fail | not_run

    # Gate artifacts (JSON encoded as Text, for display in the review pane)
    lint_report = Column(Text, nullable=True)    # {errors: [], warnings: []}
    tester_report = Column(Text, nullable=True)  # {steps: [], passed: bool}

    # Admin review outcome
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    approval_status = Column(String(20), default="pending", nullable=False)  # pending | approved | rejected | changes_requested
    reviewer_notes = Column(Text, nullable=True)

    # Audit
    submitted_at = Column(DateTime, server_default=func.now())

    # Relationships
    instance = relationship("TemplateInstance", foreign_keys=[instance_id])
    submitter = relationship("User", foreign_keys=[instructor_id])
    course = relationship("Course", foreign_keys=[course_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_pending_approval_status", "approval_status"),
        Index("ix_pending_reviewer", "reviewed_by"),
        Index("ix_pending_submitted", "submitted_at"),
        CheckConstraint("approval_status IN ('pending', 'approved', 'rejected', 'changes_requested')", name="ck_pending_approval"),
        CheckConstraint("fork_type IN ('cosmetic', 'exposed', 'full_fork')", name="ck_pending_fork_type"),
        CheckConstraint("tier IN ('parameterize', 'remix', 'author')", name="ck_pending_tier"),
    )


# ============================================================================
# Exercise Studio -- Phase 2 (AI Generate). Additive: an instructor pastes a
# syllabus, the model plans exercises mapped onto the vetted template catalog
# and proposes per-exercise cosmetic overrides; each approved item runs through
# the SAME Phase 0 materialize -> gate -> ingest path as a manual reskin. No
# free-form container authoring here (that is Phase 3). None of these tables
# touch any existing table's behaviour.
# ============================================================================


class InstructorApiKey(Base):
    """A saved LLM provider connection for AI generation (BYO).

    An instructor may have several profiles (e.g. a hosted key and a local
    Ollama endpoint); one is marked is_default. The plaintext key is never
    stored or logged, only the Fernet-encrypted token (see app.crypto). Local
    providers such as Ollama carry a base_url and no key, so encrypted_key is
    nullable. The legacy table name is kept; think of each row as a provider
    profile, not strictly an API key.
    """
    __tablename__ = "instructor_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(30), default="custom", nullable=False)  # a custom or self-hosted provider
    label = Column(String(120), nullable=True)
    base_url = Column(Text, nullable=True)          # OpenAI-compatible endpoint (Ollama/vLLM/OpenAI)
    model = Column(String(120), nullable=True)
    encrypted_key = Column(Text, nullable=True)     # nullable: Ollama needs no key
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ExerciseGenJob(Base):
    """An AI generation job: a syllabus/prompt -> N planned exercises.

    Lives entirely in the DB (PRD 5.7): the background worker advances it, and
    the browser only observes. status: planning -> awaiting_plan ->
    building -> awaiting_review -> done | failed. Tokens are accumulated for the
    audit trail.
    """
    __tablename__ = "exercise_gen_jobs"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    input_syllabus = Column(Text, nullable=True)
    params = Column(Text, nullable=True)  # JSON: {track, count, difficulty, techniques, attach}
    model = Column(String(50), default="", nullable=False)
    provider_profile_id = Column(Integer, nullable=True)  # which InstructorApiKey ran this job
    status = Column(String(30), default="planning", nullable=False)
    token_cost = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    # Job-level claim-lease (the planning step is one model call).
    claimed_by = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    items = relationship("ExerciseGenItem", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_genjob_status", "status"),
        Index("ix_genjob_instructor", "instructor_id"),
        CheckConstraint(
            "status IN ('planning', 'awaiting_plan', 'building', 'awaiting_review', 'done', 'failed')",
            name="ck_genjob_status",
        ),
    )


class ExerciseGenItem(Base):
    """One planned exercise within a job. The worker claims it and advances it
    select -> generate -> gate -> ingest, reusing template_engine + the gate.

    Tier is parameterize|remix (catalog templates) for Phase 2; author (free-form
    new infra) is recognized but parked as ``needs_infra`` until Phase 3.
    """
    __tablename__ = "exercise_gen_items"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("exercise_gen_jobs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=True)
    technique = Column(String(255), nullable=True)
    tier = Column(String(20), default="parameterize", nullable=False)
    template_slug = Column(String(150), nullable=True)   # chosen catalog template
    stage = Column(String(20), default="select", nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    overrides = Column(Text, nullable=True)   # JSON: model-proposed cosmetic overrides
    instance_id = Column(Integer, ForeignKey("template_instances.id", ondelete="SET NULL"), nullable=True)
    pending_review_id = Column(Integer, nullable=True)
    lab_id = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    # Per-item claim-lease for safe parallel build across the 17 uvicorn workers.
    claimed_by = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    job = relationship("ExerciseGenJob", back_populates="items")

    __table_args__ = (
        Index("ix_genitem_job_status", "job_id", "status"),
        CheckConstraint("tier IN ('parameterize', 'remix', 'author')", name="ck_genitem_tier"),
        CheckConstraint(
            "status IN ('pending', 'building', 'ready', 'failed', 'needs_infra', 'skipped')",
            name="ck_genitem_status",
        ),
    )
