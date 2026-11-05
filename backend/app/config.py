import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: list[str]
    groq_api_key: str
    groq_model: str
    ask_max_rows: int
    ask_timeout_ms: int

    @property
    def llm_mode(self) -> str:
        return "groq" if self.groq_api_key else "demo"


def load_settings(env=os.environ) -> Settings:
    origins = env.get("CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        database_url=env.get(
            "DATABASE_URL", "postgresql://cartlens:cartlens@localhost:5432/cartlens"
        ),
        cors_origins=[o.strip().rstrip("/") for o in origins.split(",") if o.strip()],
        groq_api_key=env.get("GROQ_API_KEY", ""),
        # Verified on console.groq.com/docs/models (Nov 2026): a production model
        # that supports strict JSON-schema structured outputs.
        groq_model=env.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        ask_max_rows=int(env.get("ASK_MAX_ROWS", "200")),
        ask_timeout_ms=int(env.get("ASK_TIMEOUT_MS", "5000")),
    )
