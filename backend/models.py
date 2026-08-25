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
    password: str
    preferred_name: Optional[str] = None


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
