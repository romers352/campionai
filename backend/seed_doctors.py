"""Idempotent demo-doctor seeder so the directory UI isn't empty in a fresh env.
Run: python seed_doctors.py
These are clearly demo profiles (email domain @demo.campionai). Safe to re-run.
"""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


def new_id():
    import uuid
    return str(uuid.uuid4())


DEMO = [
    {"name": "Dr. Aisha Rahman", "credentials": "MD, Psychiatry", "specialty": "Anxiety & mood",
     "languages": ["en", "hi", "ar"], "country": "US", "is_volunteer": False, "session_price": 45,
     "bio": "Warm, evidence-based care. 10+ years helping people through anxiety, burnout and low mood.",
     "rating_avg": 4.9, "rating_count": 128, "online": True},
    {"name": "Dr. Marco Silva", "credentials": "PsyD, Clinical Psychology", "specialty": "Stress & relationships",
     "languages": ["en", "pt", "es"], "country": "US", "is_volunteer": True, "session_price": 0,
     "bio": "Volunteer counsellor. Here for a listening ear and practical, gentle strategies.",
     "rating_avg": 4.8, "rating_count": 76, "online": True},
    {"name": "Dr. Priya Nair", "credentials": "MBBS, MD", "specialty": "Sleep & wellbeing",
     "languages": ["en", "hi"], "country": "US", "is_volunteer": False, "session_price": 30,
     "bio": "Focused on sleep, routine and everyday wellbeing. Kind, no-judgement conversations.",
     "rating_avg": 4.7, "rating_count": 54, "online": False},
    {"name": "Dr. Sophie Laurent", "credentials": "MD, Family Medicine", "specialty": "General wellbeing",
     "languages": ["en", "fr"], "country": "US", "is_volunteer": False, "session_price": 40,
     "bio": "A friendly first port of call for whatever's on your mind — big or small.",
     "rating_avg": 4.6, "rating_count": 41, "online": False},
    {"name": "Dr. James Okoro", "credentials": "MSc, Counselling", "specialty": "Grief & life changes",
     "languages": ["en"], "country": "US", "is_volunteer": True, "session_price": 0,
     "bio": "Volunteer. Specialising in grief, transitions and finding footing again.",
     "rating_avg": 5.0, "rating_count": 33, "online": True},
]


async def main():
    now = datetime.now(timezone.utc).isoformat()
    seeded = 0
    for d in DEMO:
        email = f"{d['name'].split()[1].lower()}@demo.campionai"
        existing = await db.doctors.find_one({"email": email})
        photo = f"https://ui-avatars.com/api/?name={d['name'].replace(' ', '+')}&background=1a1a1c&color=fafafa&bold=true&size=160"
        doc = {
            "id": existing["id"] if existing else new_id(),
            "user_id": existing["user_id"] if existing else f"demo-{new_id()}",
            "email": email,
            "name": d["name"],
            "credentials": d["credentials"],
            "licence_number": "DEMO-0000",
            "licence_doc_path": None,
            "photo_path": photo,
            "specialty": d["specialty"],
            "languages": d["languages"],
            "country": d["country"],
            "bio": d["bio"],
            "is_volunteer": d["is_volunteer"],
            "session_price": float(d["session_price"]),
            "currency": "usd",
            "status": "verified",
            "kyc": {"provider": "demo", "status": "approved"},
            "is_online": d["online"],
            "last_seen": now if d["online"] else None,
            "rating_avg": d["rating_avg"],
            "rating_count": d["rating_count"],
            "demo": True,
            "created_at": existing["created_at"] if existing else now,
            "updated_at": now,
        }
        await db.doctors.update_one({"email": email}, {"$set": doc}, upsert=True)
        seeded += 1
    print(f"Seeded/updated {seeded} demo doctors.")


if __name__ == "__main__":
    asyncio.run(main())
