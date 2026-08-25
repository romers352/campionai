import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
TOKEN_DAYS = 30

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str, token_version: int = 0) -> str:
    payload = {
        "sub": user_id,
        "tv": token_version,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> dict:
    """Returns the full claim set. Callers that need revocation checking should go
    through build_authenticate() rather than reading `sub` directly."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def build_authenticate(db):
    """Token -> user, enforcing revocation. Logout increments users.token_version,
    which invalidates every token already issued for that user."""
    async def authenticate(token: str):
        payload = decode_token(token)
        user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if payload.get("tv", 0) != user.get("token_version", 0):
            raise HTTPException(status_code=401, detail="Session expired")
        return user

    return authenticate


def build_get_current_user(db):
    authenticate = build_authenticate(db)

    async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
        if not creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return await authenticate(creds.credentials)

    return get_current_user


def build_get_admin_user(get_current_user):
    async def get_admin_user(user=Depends(get_current_user)):
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        return user

    return get_admin_user


def build_get_doctor_user(get_current_user, db):
    """A verified doctor: role must be `doctor` AND their doctors row approved.
    Pending/rejected/suspended applicants authenticate fine but reach nothing."""
    async def get_doctor_user(user=Depends(get_current_user)):
        if user.get("role") != "doctor":
            raise HTTPException(status_code=403, detail="Doctor access required")
        doc = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=403, detail="No doctor profile")
        if doc.get("status") != "verified":
            raise HTTPException(status_code=403, detail=f"Doctor profile is {doc.get('status', 'pending')}")
        user["doctor"] = doc
        return user

    return get_doctor_user
