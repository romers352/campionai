"""Model router: routes tasks to cheap/medium/powerful models.
Supports Emergent universal key (OpenAI/Anthropic/Gemini) and OpenRouter (admin-configurable)."""
import os
import json
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_ROUTES = {
    "cheap": {"provider": "emergent-openai", "model": "gpt-5.4-mini"},
    "medium": {"provider": "emergent-anthropic", "model": "claude-sonnet-4-6"},
    "powerful": {"provider": "emergent-anthropic", "model": "claude-opus-4-6"},
}

EMERGENT_PROVIDER_MAP = {
    "emergent-openai": "openai",
    "emergent-anthropic": "anthropic",
    "emergent-gemini": "gemini",
}


class ModelRouter:
    def __init__(self, db):
        self.db = db

    async def _routes(self):
        routes = dict(DEFAULT_ROUTES)
        async for doc in self.db.model_config.find({}, {"_id": 0}):
            if doc.get("tier") in routes:
                routes[doc["tier"]] = {"provider": doc["provider"], "model": doc["model"]}
        return routes

    async def _settings(self):
        s = await self.db.provider_settings.find_one({"id": "global"}, {"_id": 0})
        if not s:
            s = {
                "llm_provider": os.environ.get("LLM_PROVIDER", "emergent"),
                "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
            }
        return s

    async def route_for(self, tier):
        routes = await self._routes()
        return routes.get(tier, DEFAULT_ROUTES["medium"])

    async def complete(self, system: str, user_text: str, tier: str, session_id: str) -> str:
        """Non-streaming completion for classification / memory extraction."""
        route = await self.route_for(tier)
        settings = await self._settings()
        if route["provider"] == "openrouter" or settings.get("llm_provider") == "openrouter":
            return await self._openrouter(system, user_text, route["model"], settings, stream=False)
        return await self._emergent(system, user_text, route, session_id, stream=False)

    async def stream(self, system: str, user_text: str, tier: str, session_id: str):
        route = await self.route_for(tier)
        settings = await self._settings()
        if route["provider"] == "openrouter" or settings.get("llm_provider") == "openrouter":
            async for chunk in self._openrouter_stream(system, user_text, route["model"], settings):
                yield chunk
        else:
            async for chunk in self._emergent_stream(system, user_text, route, session_id):
                yield chunk

    # ---------- Emergent ----------
    def _emergent_chat(self, system, route, session_id):
        provider = EMERGENT_PROVIDER_MAP.get(route["provider"], "anthropic")
        model = route["model"]
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system)
        chat.with_model(provider, model)
        return chat

    async def _emergent(self, system, user_text, route, session_id, stream=False):
        chat = self._emergent_chat(system, route, session_id)
        resp = await chat.send_message(UserMessage(text=user_text))
        return resp if isinstance(resp, str) else str(resp)

    async def _emergent_stream(self, system, user_text, route, session_id):
        from emergentintegrations.llm.chat import TextDelta, StreamDone
        chat = self._emergent_chat(system, route, session_id)
        async for ev in chat.stream_message(UserMessage(text=user_text)):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                break

    # ---------- OpenRouter ----------
    def _or_key(self, settings):
        return settings.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")

    async def _openrouter(self, system, user_text, model, settings, stream=False):
        key = self._or_key(settings)
        if not key:
            raise RuntimeError("OpenRouter API key not configured")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def _openrouter_stream(self, system, user_text, model, settings):
        key = self._or_key(settings)
        if not key:
            raise RuntimeError("OpenRouter API key not configured")
        payload = {
            "model": model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", OPENROUTER_URL, json=payload, headers=headers) as r:
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue


async def list_openrouter_models(api_key: str):
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return []
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
        r.raise_for_status()
        data = r.json().get("data", [])
        return [{"id": m["id"], "name": m.get("name", m["id"])} for m in data]
