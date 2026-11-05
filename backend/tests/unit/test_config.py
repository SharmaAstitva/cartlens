from app.config import load_settings


def test_defaults_point_at_local_docker_db():
    s = load_settings({})
    assert s.database_url == "postgresql://cartlens:cartlens@localhost:5432/cartlens"
    assert s.cors_origins == ["http://localhost:5173"]
    assert s.llm_mode == "demo"
    assert s.groq_model == "openai/gpt-oss-120b"
    assert s.ask_max_rows == 200


def test_reads_environment():
    s = load_settings(
        {
            "DATABASE_URL": "postgresql://u:p@h/db",
            "CORS_ORIGINS": "https://a.vercel.app/, http://localhost:5173 ,",
            "GROQ_API_KEY": "gsk_x",
            "ASK_MAX_ROWS": "50",
        }
    )
    assert s.database_url == "postgresql://u:p@h/db"
    assert s.cors_origins == ["https://a.vercel.app", "http://localhost:5173"]
    assert s.llm_mode == "groq"
    assert s.ask_max_rows == 50
