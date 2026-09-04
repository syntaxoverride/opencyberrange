"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
import re


def _validate_password(v: str) -> str:
    """Shared password complexity check used by all schemas that accept passwords."""
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'[0-9]', v):
        raise ValueError('Password must contain at least one number')
    return v


# ==================== User Schemas ====================

class UserBase(BaseModel):
    username: str
    email: EmailStr
    student_id: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    student_id: Optional[str] = None
    is_active: Optional[bool] = True
    is_approved: Optional[bool] = False
    is_admin: Optional[bool] = False
    role: Optional[str] = "student"
    must_change_password: Optional[bool] = False

    class Config:
        from_attributes = True


class UserAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    student_id: Optional[str] = None
    is_active: Optional[bool] = True
    is_approved: Optional[bool] = False
    is_admin: Optional[bool] = False
    role: Optional[str] = "student"
    is_locked: Optional[bool] = False
    failed_attempts: Optional[int] = 0
    locked_at: Optional[datetime] = None
    vpn_registered: Optional[bool] = False
    must_change_password: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LabCompletionDetail(BaseModel):
    """Lab completion information for user detail view"""
    lab_id: int
    lab_name: str
    lab_slug: str
    track_name: Optional[str] = None
    level_number: Optional[int] = None
    completed_at: datetime
    attempts: int
    hints_used: int
    time_spent_minutes: Optional[int] = None
    
    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """Detailed user information with completions and statistics"""
    id: int
    username: str
    email: str
    student_id: Optional[str] = None
    is_active: Optional[bool] = True
    is_approved: Optional[bool] = False
    is_admin: Optional[bool] = False
    role: Optional[str] = "student"
    is_locked: Optional[bool] = False
    failed_attempts: Optional[int] = 0
    locked_at: Optional[datetime] = None
    vpn_registered: Optional[bool] = False
    must_change_password: Optional[bool] = False
    created_at: Optional[datetime] = None

    # Statistics
    total_labs_completed: int = 0
    total_flag_attempts: int = 0
    total_hints_used: int = 0
    average_time_per_lab: Optional[float] = None
    
    # Related data
    completions: List[LabCompletionDetail] = []
    active_sessions: List["LabSessionResponse"] = []
    
    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    student_id: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=128)
    is_approved: bool = False
    is_admin: bool = False
    role: Optional[str] = "student"

    @field_validator('password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator('role')
    @classmethod
    def role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('student', 'instructor', 'admin'):
            raise ValueError('Role must be student, instructor, or admin')
        return v


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    is_admin: Optional[bool] = None
    role: Optional[str] = None
    must_change_password: Optional[bool] = None

    @field_validator('role')
    @classmethod
    def role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('student', 'instructor', 'admin'):
            raise ValueError('Role must be student, instructor, or admin')
        return v

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        """Username must start with letter and contain only alphanumeric, underscore, hyphen"""
        if v is None:
            return None
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Username must start with a letter and contain only letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('password')
    @classmethod
    def password_strong(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_password(v)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        return _validate_password(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @field_validator('new_password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        return _validate_password(v)


# ==================== Lab Schemas ====================

class LabResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    difficulty: str
    category: str
    duration_minutes: int
    is_active: Optional[bool] = True
    level_id: Optional[int] = None
    sort_order: int
    
    class Config:
        from_attributes = True


class UpdateLabRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    is_course_exclusive: Optional[bool] = None  # Deprecated — use visibility
    is_course_available: Optional[bool] = None  # Deprecated — use visibility
    visibility: Optional[str] = None  # draft | course | pending_public | public
    level_id: Optional[int] = None  # Send explicit null to clear (uncategorize); omit key to leave unchanged

    @field_validator('visibility')
    @classmethod
    def visibility_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('draft', 'course', 'pending_public', 'public'):
            raise ValueError('Visibility must be draft, course, pending_public, or public')
        return v


# ==================== Lab Session Schemas ====================

class TargetInfo(BaseModel):
    name: str
    ip: str
    ports: List[int] = []


class LabSessionResponse(BaseModel):
    id: int
    lab_id: int
    lab_name: str
    lab_slug: str
    network_subnet: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    targets: List[TargetInfo] = []
    
    class Config:
        from_attributes = True


# ==================== VPN Schemas ====================

class VPNStatusResponse(BaseModel):
    has_config: bool
    vpn_registered: Optional[bool] = False
    client_ip: Optional[str] = None


# ==================== Auth Schemas ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# NOTE: the registration request model is NOT here. It lives in
# app/routers/auth.py, because that is the one the /api/auth/register
# endpoint binds, and it carries the invite_code field that this module
# never had. A duplicate RegisterRequest used to sit here with no
# invite_code, which made it look like the backend could not accept an
# invite code at all. Removed rather than kept in sync.


# ==================== Course Schemas ====================

class CourseCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    code: str = Field(..., min_length=2, max_length=20)
    semester: str = Field(..., min_length=3, max_length=20)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    instructor_id: Optional[int] = None
    wiki_theme_color: Optional[str] = None


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=150)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    semester: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
    instructor_id: Optional[int] = None
    wiki_theme_color: Optional[str] = None


class CourseResponse(BaseModel):
    id: int
    name: str
    code: str
    semester: str
    description: Optional[str] = None
    invite_code: str
    instructor_id: int
    instructor_name: Optional[str] = None
    start_date: datetime
    end_date: datetime
    is_active: bool
    is_archived: bool = False
    wiki_slug: Optional[str] = None
    wiki_theme_color: Optional[str] = "blue"
    created_at: Optional[datetime] = None
    student_count: int = 0
    lab_count: int = 0

    class Config:
        from_attributes = True


class CourseJoinRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=20)


class CourseLabAssignRequest(BaseModel):
    lab_ids: List[int]


class CourseLabReorderRequest(BaseModel):
    lab_order: List[dict]


class AssignmentReorderRequest(BaseModel):
    assignment_order: List[dict]


class CourseLabUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)


class BulkEnrollRequest(BaseModel):
    user_ids: List[int]


class ScoreboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    student_id: Optional[str] = None
    total_score: int
    labs_completed: int
    achievements: List[str] = []
    lab_scores: dict = {}


class ScoreboardResponse(BaseModel):
    course: dict
    labs: List[dict]
    scoreboard: List[ScoreboardEntry]


class AchievementResponse(BaseModel):
    id: int
    user_id: int
    username: str
    achievement_type: str
    lab_id: Optional[int] = None
    lab_name: Optional[str] = None
    awarded_at: datetime

    class Config:
        from_attributes = True


# ==================== Assignment Schemas ====================

class AssignmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    locked: Optional[bool] = False


class AssignmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    locked: Optional[bool] = None


class AssignmentLabsRequest(BaseModel):
    lab_ids: List[int]


# ==================== Dashboard Schemas ====================

class DashboardStatsResponse(BaseModel):
    active_sessions: int = 0
    submission_rate: int = 0
    pending_approvals: int = 0
    course_activity: int = 0


class ActivityEventResponse(BaseModel):
    id: int
    event_type: str
    event_label: str = ""
    actor_id: Optional[int] = None
    actor_username: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_label: Optional[str] = None
    detail: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PulseDataPoint(BaseModel):
    hour: str
    concurrent_labs: int = 0
    flags_submitted: int = 0


class PulseResponse(BaseModel):
    data: List[PulseDataPoint] = []


class StudentDashboardResponse(BaseModel):
    next_objective: Optional[dict] = None
    progress_percent: int = 0
    total_labs: int = 0
    completed_labs: int = 0
    vpn_status: Optional[dict] = None
    scoreboard_rank: Optional[int] = None
    course_name: Optional[str] = None


# ==================== Settings Schemas ====================

class SettingsBulkUpdate(BaseModel):
    settings: dict  # {"key": "value", ...}


# ==================== Curriculum Admin Schemas ====================

class TrackCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = "web"
    color: Optional[str] = "#3b82f6"

    @field_validator('slug')
    @classmethod
    def slug_valid(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9-]*$', v):
            raise ValueError('Slug must start with lowercase letter and contain only lowercase letters, numbers, and hyphens')
        return v


class TrackUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class LevelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class LevelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class ReorderRequest(BaseModel):
    ordered_ids: List[int]


# ==================== Lab Creation & Flag Schemas ====================

class LabCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    scenario: Optional[str] = None
    difficulty: str = "beginner"
    category: str = "general"
    duration_minutes: int = 60
    level_id: Optional[int] = None
    compose_file: str = ""
    objectives: Optional[str] = None
    hints: Optional[str] = None
    tools: Optional[str] = None
    hostnames: Optional[str] = None
    flag: Optional[str] = None
    visibility: Optional[str] = None
    lab_yaml: Optional[str] = None
    @field_validator('slug')
    @classmethod
    def slug_valid(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9-]*$', v):
            raise ValueError('Slug must start with lowercase letter and contain only lowercase letters, numbers, and hyphens')
        return v


class SetupRequest(BaseModel):
    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=128)
    require_approval: Optional[bool] = True
    # One-time install token; required only when the server sets SETUP_TOKEN
    # (see /setup/complete). Blank on isolated installs that don't set it.
    setup_token: Optional[str] = None

    @field_validator('admin_password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        return _validate_password(v)








# ==================== Impersonation Schemas ====================

class ImpersonateRequest(BaseModel):
    target_user_id: Optional[int] = None
    target_role: Optional[str] = None
    course_id: Optional[int] = None

    @field_validator('target_role')
    @classmethod
    def target_role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('student', 'instructor'):
            raise ValueError('target_role must be student or instructor')
        return v


class ImpersonateResponse(BaseModel):
    token: str
    impersonated_user: dict
    original_user: dict
    mode: str  # "user" | "role_course" | "role_global"
    expires_in: int


# Update forward references after all models are defined
UserDetailResponse.update_forward_refs()

