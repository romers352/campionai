"""Doctor directory, applications, verification, availability, and payouts.

Built as a router factory (the same dependency-injection shape auth.py already uses)
so it can reach the db and the auth dependencies without importing server.py.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

import kyc
from models import (
    DoctorApply, DoctorProfileUpdate, DoctorStatusUpdate, OnlineToggle,
    AvailabilityInput, PayoutSettle, ConsultSettings, now_iso, new_id,
)
from notifications import send_email

logger = logging.getLogger("campionai.doctors")

# A doctor who hasn't pinged in this long is treated as offline regardless of the flag,
# so a crashed tab can't leave a ghost sitting at the top of the directory.
PRESENCE_TIMEOUT_SEC = 90

DEFAULT_SETTINGS = {"commission_pct": 15.0, "free_volunteer_sessions_per_month": 2}


async def get_consult_settings(db) -> dict:
    s = await db.provider_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    return {**DEFAULT_SETTINGS, **(s.get("consult_settings") or {})}


def is_online(doc: dict) -> bool:
    """Flag AND a recent heartbeat — the flag alone survives a browser crash."""
    if not doc.get("is_online"):
        return False
    last = doc.get("last_seen")
    if not last:
        return False
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() < PRESENCE_TIMEOUT_SEC
    except Exception:
        return False


def public_doctor(d: dict) -> dict:
    """What a patient may see before a session exists. Contact details and licence
    data stay server-side until they actually book."""
    return {
        "id": d["id"],
        "name": d.get("name"),
        "credentials": d.get("credentials"),
        "specialty": d.get("specialty"),
        "languages": d.get("languages", []),
        "country": d.get("country"),
        "bio": d.get("bio"),
        "photo_path": d.get("photo_path"),
        "is_volunteer": bool(d.get("is_volunteer")),
        "session_price": float(d.get("session_price", 0) or 0),
        "rating_avg": round(float(d.get("rating_avg", 0) or 0), 2),
        "rating_count": int(d.get("rating_count", 0) or 0),
        "is_online": is_online(d),
    }


def make_router(db, get_current_user, get_admin_user, get_doctor_user) -> APIRouter:
    r = APIRouter()

    # ---------------- Public directory ----------------
    @r.get("/doctors")
    async def list_doctors(
        country: str = Query(None),
        language: str = Query(None),
        volunteer_only: bool = Query(False),
        online_only: bool = Query(False),
        user=Depends(get_current_user),
    ):
        """Matching is country + language — for a remote consult those are what
        actually matter (timezone, jurisdiction, being understood)."""
        q = {"status": "verified"}
        country = (country or user.get("country") or "").upper() or None
        if country:
            q["country"] = country
        if language:
            q["languages"] = language
        if volunteer_only:
            q["is_volunteer"] = True

        docs = await db.doctors.find(q, {"_id": 0}).to_list(200)
        # Country is a preference, not a hard filter — an empty list helps nobody.
        if not docs and country:
            q.pop("country", None)
            docs = await db.doctors.find(q, {"_id": 0}).to_list(200)

        out = [public_doctor(d) for d in docs]
        if online_only:
            out = [d for d in out if d["is_online"]]
        out.sort(key=lambda d: (not d["is_online"], -d["rating_avg"], -d["rating_count"]))
        return out

    @r.get("/doctors/{doctor_id}")
    async def get_doctor(doctor_id: str, user=Depends(get_current_user)):
        d = await db.doctors.find_one({"id": doctor_id, "status": "verified"}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Doctor not found")
        ratings = await db.doctor_ratings.find(
            {"doctor_id": doctor_id, "comment": {"$nin": [None, ""]}}, {"_id": 0, "stars": 1, "comment": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(20)
        avail = await db.doctor_availability.find({"doctor_id": doctor_id}, {"_id": 0}).sort("weekday", 1).to_list(50)
        return {**public_doctor(d), "reviews": ratings, "availability": avail}

    # ---------------- Applying ----------------
    @r.post("/doctor/apply")
    async def apply(inp: DoctorApply, request: Request, user=Depends(get_current_user)):
        existing = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0})
        if existing and existing.get("status") in ("pending", "verified"):
            raise HTTPException(status_code=400, detail=f"You already have a {existing['status']} application")

        price = 0.0 if inp.is_volunteer else round(float(inp.session_price), 2)
        if not inp.is_volunteer and price <= 0:
            raise HTTPException(status_code=400, detail="Set a session price, or apply as a volunteer")

        doc = {
            "id": existing["id"] if existing else new_id(),
            "user_id": user["id"],
            "email": user["email"],
            "name": inp.name,
            "credentials": inp.credentials,
            "licence_number": inp.licence_number,
            "licence_doc_path": inp.licence_doc_path,
            "photo_path": inp.photo_path,
            "specialty": inp.specialty,
            "languages": [lang.strip().lower() for lang in inp.languages if lang.strip()] or ["en"],
            "country": inp.country.upper(),
            "bio": inp.bio,
            "is_volunteer": bool(inp.is_volunteer),
            "session_price": price,
            "currency": "usd",
            "status": "pending",
            "kyc": (existing or {}).get("kyc") or {"provider": kyc.PROVIDER, "status": "not_started"},
            "is_online": False,
            "last_seen": None,
            "rating_avg": 0.0,
            "rating_count": 0,
            "created_at": (existing or {}).get("created_at") or now_iso(),
            "updated_at": now_iso(),
        }
        await db.doctors.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
        await db.users.update_one({"id": user["id"]}, {"$set": {"role": "doctor"}})
        return doc

    @r.get("/doctor/me")
    async def doctor_me(user=Depends(get_current_user)):
        d = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="No doctor profile")
        return d

    @r.post("/doctor/kyc/start")
    async def kyc_start(request: Request, user=Depends(get_current_user)):
        d = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Apply first")
        if not kyc.configured():
            await db.doctors.update_one({"user_id": user["id"]}, {"$set": {"kyc.status": "not_configured"}})
            raise HTTPException(status_code=503, detail="Identity verification is not configured yet — an admin will review manually")
        callback = f"{str(request.base_url).rstrip('/')}/api/webhook/kyc"
        session = await kyc.create_session(user["id"], callback)
        if not session:
            raise HTTPException(status_code=502, detail="Could not start identity verification")
        await db.doctors.update_one({"user_id": user["id"]}, {"$set": {
            "kyc": {"provider": kyc.PROVIDER, "session_id": session["session_id"],
                    "status": "pending", "started_at": now_iso()},
        }})
        return {"url": session["url"], "session_id": session["session_id"]}

    @r.get("/doctor/kyc/refresh")
    async def kyc_refresh(user=Depends(get_current_user)):
        """Polling fallback for when the webhook never arrives."""
        d = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0})
        if not d or not (d.get("kyc") or {}).get("session_id"):
            raise HTTPException(status_code=404, detail="No verification in progress")
        status = await kyc.get_status(d["kyc"]["session_id"])
        await db.doctors.update_one({"user_id": user["id"]},
                                    {"$set": {"kyc.status": status, "kyc.checked_at": now_iso()}})
        return {"status": status}

    @r.post("/webhook/kyc")
    async def kyc_webhook(request: Request):
        body = await request.body()
        sig = request.headers.get("x-signature") or request.headers.get("x-hub-signature-256", "")
        if not kyc.verify_webhook(body, sig, request.headers.get("x-timestamp")):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        import json
        try:
            event = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed webhook")
        session_id = event.get("session_id") or event.get("id")
        user_id = event.get("vendor_data")
        status = kyc.normalize_status(event.get("status") or event.get("decision", {}).get("status"))
        q = {"kyc.session_id": session_id} if session_id else ({"user_id": user_id} if user_id else None)
        if not q:
            return {"status": "ignored"}
        await db.doctors.update_one(q, {"$set": {"kyc.status": status, "kyc.checked_at": now_iso()}})
        logger.info(f"kyc webhook: session={session_id} -> {status}")
        return {"status": "ok"}

    # ---------------- Verified-doctor self service ----------------
    @r.put("/doctor/profile")
    async def update_profile(inp: DoctorProfileUpdate, user=Depends(get_doctor_user)):
        patch = {k: v for k, v in inp.model_dump().items() if v is not None}
        if patch.get("is_volunteer"):
            patch["session_price"] = 0.0
        if "languages" in patch:
            patch["languages"] = [lang.strip().lower() for lang in patch["languages"] if lang.strip()] or ["en"]
        if patch.get("session_price") is not None and not patch.get("is_volunteer", user["doctor"].get("is_volunteer")):
            if float(patch.get("session_price", 0)) <= 0:
                raise HTTPException(status_code=400, detail="Set a session price, or switch to volunteering")
        patch["updated_at"] = now_iso()
        await db.doctors.update_one({"id": user["doctor"]["id"]}, {"$set": patch})
        return await db.doctors.find_one({"id": user["doctor"]["id"]}, {"_id": 0})

    @r.put("/doctor/online")
    async def set_online(inp: OnlineToggle, user=Depends(get_doctor_user)):
        await db.doctors.update_one({"id": user["doctor"]["id"]}, {"$set": {
            "is_online": bool(inp.is_online), "last_seen": now_iso(),
        }})
        return {"is_online": bool(inp.is_online)}

    @r.post("/doctor/heartbeat")
    async def heartbeat(user=Depends(get_doctor_user)):
        await db.doctors.update_one({"id": user["doctor"]["id"]}, {"$set": {"last_seen": now_iso()}})
        return {"ok": True}

    @r.get("/doctor/availability")
    async def get_availability(user=Depends(get_doctor_user)):
        return await db.doctor_availability.find(
            {"doctor_id": user["doctor"]["id"]}, {"_id": 0}).sort("weekday", 1).to_list(100)

    @r.post("/doctor/availability")
    async def add_availability(inp: AvailabilityInput, user=Depends(get_doctor_user)):
        if inp.start >= inp.end:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        doc = {"id": new_id(), "doctor_id": user["doctor"]["id"], **inp.model_dump(), "created_at": now_iso()}
        await db.doctor_availability.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    @r.delete("/doctor/availability/{slot_id}")
    async def delete_availability(slot_id: str, user=Depends(get_doctor_user)):
        res = await db.doctor_availability.delete_one({"id": slot_id, "doctor_id": user["doctor"]["id"]})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Slot not found")
        return {"ok": True}

    @r.get("/doctor/earnings")
    async def earnings(user=Depends(get_doctor_user)):
        did = user["doctor"]["id"]
        sessions = await db.consult_sessions.find(
            {"doctor_id": did, "status": "completed", "price": {"$gt": 0}}, {"_id": 0}
        ).sort("ended_at", -1).to_list(500)
        unsettled = sum(float(s.get("doctor_earning", 0) or 0) for s in sessions if s.get("payout_status") != "settled")
        settled = sum(float(s.get("doctor_earning", 0) or 0) for s in sessions if s.get("payout_status") == "settled")
        payouts = await db.doctor_payouts.find({"doctor_id": did}, {"_id": 0}).sort("created_at", -1).to_list(50)
        return {
            "unsettled": round(unsettled, 2), "settled": round(settled, 2),
            "sessions": len(sessions), "payouts": payouts,
        }

    # ---------------- Admin ----------------
    @r.get("/admin/doctors")
    async def admin_list(status: str = Query(None), admin=Depends(get_admin_user)):
        q = {"status": status} if status else {}
        return await db.doctors.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)

    @r.put("/admin/doctors/{doctor_id}/status")
    async def admin_set_status(doctor_id: str, inp: DoctorStatusUpdate, admin=Depends(get_admin_user)):
        if inp.status not in ("pending", "verified", "rejected", "suspended"):
            raise HTTPException(status_code=400, detail="Unknown status")
        d = await db.doctors.find_one({"id": doctor_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Identity check and licence check are separate gates; approving without the
        # first is a deliberate override, so record who did it and why.
        kyc_status = (d.get("kyc") or {}).get("status")
        if inp.status == "verified" and kyc_status != "approved" and not inp.reason:
            raise HTTPException(
                status_code=400,
                detail=f"Identity verification is '{kyc_status or 'not started'}'. Approve anyway by giving a reason.",
            )

        patch = {"status": inp.status, "review_reason": inp.reason,
                 "reviewed_by": admin["email"], "reviewed_at": now_iso(), "updated_at": now_iso()}
        if inp.status != "verified":
            patch["is_online"] = False
        await db.doctors.update_one({"id": doctor_id}, {"$set": patch})

        if d.get("email"):
            if inp.status == "verified":
                subject, msg = "You're verified on CampionAI", "Your application has been approved — you can now take sessions."
            elif inp.status == "rejected":
                subject, msg = "Your CampionAI application", f"We couldn't approve your application. {inp.reason or ''}".strip()
            else:
                subject, msg = "Your CampionAI doctor account", f"Your account status is now: {inp.status}."
            await send_email(d["email"], subject,
                             f"<div style='font-family:sans-serif;line-height:1.6'><p>{msg}</p></div>")
        return await db.doctors.find_one({"id": doctor_id}, {"_id": 0})

    @r.get("/admin/consult-settings")
    async def get_settings(admin=Depends(get_admin_user)):
        return await get_consult_settings(db)

    @r.put("/admin/consult-settings")
    async def set_settings(inp: ConsultSettings, admin=Depends(get_admin_user)):
        await db.provider_settings.update_one(
            {"id": "global"}, {"$set": {"consult_settings": inp.model_dump()}}, upsert=True)
        return await get_consult_settings(db)

    @r.get("/admin/payouts")
    async def admin_payouts(admin=Depends(get_admin_user)):
        """Per-doctor unsettled totals. Settlement happens off-platform; this is the
        ledger that tells you what to send."""
        pipeline = [
            {"$match": {"status": "completed", "price": {"$gt": 0}, "payout_status": {"$ne": "settled"}}},
            {"$group": {"_id": "$doctor_id",
                        "owed": {"$sum": "$doctor_earning"},
                        "commission": {"$sum": "$commission"},
                        "sessions": {"$sum": 1}}},
            {"$sort": {"owed": -1}},
        ]
        rows = await db.consult_sessions.aggregate(pipeline).to_list(500)
        out = []
        for row in rows:
            d = await db.doctors.find_one({"id": row["_id"]}, {"_id": 0, "name": 1, "email": 1, "country": 1})
            out.append({
                "doctor_id": row["_id"],
                "name": (d or {}).get("name", "Unknown"),
                "email": (d or {}).get("email"),
                "country": (d or {}).get("country"),
                "owed": round(row["owed"], 2),
                "commission": round(row["commission"], 2),
                "sessions": row["sessions"],
            })
        return out

    @r.post("/admin/payouts/settle")
    async def settle_payout(inp: PayoutSettle, admin=Depends(get_admin_user)):
        sessions = await db.consult_sessions.find(
            {"doctor_id": inp.doctor_id, "status": "completed", "price": {"$gt": 0},
             "payout_status": {"$ne": "settled"}}, {"_id": 0, "id": 1, "doctor_earning": 1}
        ).to_list(1000)
        if not sessions:
            raise HTTPException(status_code=400, detail="Nothing outstanding for this doctor")
        total = round(sum(float(s.get("doctor_earning", 0) or 0) for s in sessions), 2)
        payout = {
            "id": new_id(), "doctor_id": inp.doctor_id, "amount": total,
            "session_ids": [s["id"] for s in sessions], "session_count": len(sessions),
            "note": inp.note, "settled_by": admin["email"], "created_at": now_iso(),
        }
        await db.doctor_payouts.insert_one(dict(payout))
        await db.consult_sessions.update_many(
            {"id": {"$in": [s["id"] for s in sessions]}},
            {"$set": {"payout_status": "settled", "payout_id": payout["id"], "settled_at": now_iso()}},
        )
        payout.pop("_id", None)
        return payout

    return r
