"""Fish Audio TTS (bring-your-own key). Returns mp3 bytes for CampionAI's voice.
STT is handled client-side via the browser Web Speech API (no server key needed)."""
import os
import httpx

FISH_TTS_URL = "https://api.fish.audio/v1/tts"


async def synthesize(text: str, api_key: str, voice_id: str | None, model: str = "s2.1-pro") -> bytes:
    key = (api_key or os.environ.get("FISH_AUDIO_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("Fish Audio API key not configured")
    payload = {"text": text[:2000], "format": "mp3"}
    vid = (voice_id or os.environ.get("FISH_AUDIO_VOICE_ID", "")).strip()
    if vid:
        payload["reference_id"] = vid
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "model": model,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(FISH_TTS_URL, json=payload, headers=headers)
        r.raise_for_status()
        return r.content
