from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ---------- Auth ----------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    preferred_name: Optional[str] = None
    as_doctor: bool = False


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionInput(BaseModel):
    session_id: str


class TrustedContact(BaseModel):
    name: str
    relationship: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CoreProfile(BaseModel):
    preferred_name: Optional[str] = None
    work: Optional[str] = None
    education: Optional[str] = None
    likes: List[str] = Field(default_factory=list)
    important_people: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    communication_style: Optional[str] = None


class OnboardingInput(BaseModel):
    preferred_name: str
    age_confirmed: bool
    country: str
    trusted_contact: TrustedContact
    safety_consent: bool
    checkin_frequency: str = "daily"
    communication_style: Optional[str] = "warm"


class ProfileUpdate(BaseModel):
    preferred_name: Optional[str] = None
    work: Optional[str] = None
    education: Optional[str] = None
    likes: Optional[List[str]] = None
    important_people: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    communication_style: Optional[str] = None
    checkin_frequency: Optional[str] = None
    country: Optional[str] = None
    trusted_contact: Optional[TrustedContact] = None


# ---------- Chat ----------
class ChatInput(BaseModel):
    session_id: Optional[str] = None
    message: str
    private: bool = False
    image_path: Optional[str] = None


class SessionCreate(BaseModel):
    title: Optional[str] = None
    private: bool = False


# ---------- Memory ----------
class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None
    tier: Optional[str] = None


# ---------- Admin ----------
class ModelRouteConfig(BaseModel):
    tier: str  # cheap | medium | powerful
    provider: str  # emergent-openai | emergent-anthropic | emergent-gemini | openrouter
    model: str


class ProfessionalInput(BaseModel):
    name: str
    credentials: str
    specialty: str
    contact: str
    verified: bool = True
    availability: str = "on-call"


class ProviderSettings(BaseModel):
    llm_provider: str  # emergent | openrouter
    openrouter_api_key: Optional[str] = None


class PrivateModeInput(BaseModel):
    enabled: bool


class VoiceSettingsInput(BaseModel):
    enabled: bool = True
    voice_id: Optional[str] = None
    fish_audio_api_key: Optional[str] = None


class TTSInput(BaseModel):
    text: str


# ---------- Payments & Wellness ----------
class CheckoutInput(BaseModel):
    package_id: str
    origin_url: str
    amount: Optional[float] = None
    anonymous: bool = False


class FoodInput(BaseModel):
    text: str
    date: Optional[str] = None


class EventInput(BaseModel):
    title: str
    start: str
    end: Optional[str] = None
    type: Optional[str] = "task"
    notes: Optional[str] = None


class PlanItemToggle(BaseModel):
    item_index: int


class PaypalActivate(BaseModel):
    subscription_id: str
    plan_key: str  # "monthly" | "yearly"


class DonationOrder(BaseModel):
    amount: float = Field(ge=1, le=10000)
    anonymous: bool = False


# ---------- Doctors ----------
class DoctorApply(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    credentials: str = Field(min_length=2, max_length=200)
    licence_number: str = Field(min_length=2, max_length=80)
    specialty: str = Field(max_length=200)
    languages: List[str] = Field(default_factory=lambda: ["en"], max_length=10)
    country: str = Field(min_length=2, max_length=2)
    bio: Optional[str] = Field(default=None, max_length=2000)
    is_volunteer: bool = False
    session_price: float = Field(default=0, ge=0, le=1000)
    licence_doc_path: Optional[str] = None
    photo_path: Optional[str] = None


class DoctorProfileUpdate(BaseModel):
    specialty: Optional[str] = Field(default=None, max_length=200)
    languages: Optional[List[str]] = Field(default=None, max_length=10)
    bio: Optional[str] = Field(default=None, max_length=2000)
    is_volunteer: Optional[bool] = None
    session_price: Optional[float] = Field(default=None, ge=0, le=1000)
    photo_path: Optional[str] = None


class DoctorStatusUpdate(BaseModel):
    status: str  # verified | rejected | suspended | pending
    reason: Optional[str] = Field(default=None, max_length=500)


class OnlineToggle(BaseModel):
    is_online: bool


class AvailabilityInput(BaseModel):
    weekday: int = Field(ge=0, le=6)  # 0 = Monday
    start: str  # "09:00"
    end: str    # "17:00"
    timezone: str = "UTC"


# ---------- Consultations ----------
class ConsultBook(BaseModel):
    doctor_id: str
    scheduled_at: str          # ISO8601 UTC
    mode: str = "video"        # video | audio | chat
    note: Optional[str] = Field(default=None, max_length=1000)


class ConsultRequest(BaseModel):
    """Instant 'talk now'. doctor_id optional — omit to broadcast to any matching doctor.

    `crisis` is a request, not a claim: the server only honours it when it can find a
    recent high-risk safety event for this user. Otherwise anyone could set the flag
    and walk past the free-session cap.
    """
    doctor_id: Optional[str] = None
    mode: str = "video"
    note: Optional[str] = Field(default=None, max_length=1000)
    crisis: bool = False


class ConsultRate(BaseModel):
    stars: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


class PayoutSettle(BaseModel):
    doctor_id: str
    note: Optional[str] = Field(default=None, max_length=500)


class ConsultSettings(BaseModel):
    commission_pct: float = Field(default=15, ge=0, le=100)
    free_volunteer_sessions_per_month: int = Field(default=2, ge=0, le=100)


# ---------- Contact ----------
class ContactInput(BaseModel):
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
