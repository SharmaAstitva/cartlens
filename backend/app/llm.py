"""Minimal Groq chat-completions client (OpenAI-compatible API) using structured outputs."""

import json

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(RuntimeError):
    pass


def parse_json(text: str) -> dict:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"The model did not return JSON: {text[:200]!r}") from exc
    if not isinstance(data, dict):
        raise LLMError("The model returned JSON, but not an object.")
    return data


class GroqClient:
    def __init__(self, api_key: str, model: str, http: httpx.Client | None = None):
        self.api_key = api_key
        self.model = model
        self.http = http or httpx.Client(timeout=30)

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "strict": True, "schema": schema},
            },
        }
        try:
            res = self.http.post(
                GROQ_URL, json=body, headers={"Authorization": f"Bearer {self.api_key}"}
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach Groq: {exc}") from exc
        if res.status_code != 200:
            raise LLMError(f"Groq returned {res.status_code}: {res.text[:300]}")
        try:
            content = res.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("Unexpected response shape from Groq.") from exc
        return parse_json(content)
