"""FastAPI app: dashboard endpoints + Ask your data."""

from __future__ import annotations

from contextlib import asynccontextmanager

import psycopg
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout
from pydantic import BaseModel, Field

from app import queries
from app.ask import EXAMPLES, AskError, AskUnavailable, ask
from app.config import Settings, load_settings
from app.llm import GroqClient


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


def get_conn(request: Request):
    with request.app.state.pool.connection(timeout=10) as conn:
        yield conn


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool.open()
        yield
        app.state.pool.close()

    app = FastAPI(
        title="CartLens API",
        description="Customer intelligence for an Indian D2C store, built on a dbt-modelled warehouse.",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=5,
        open=False,
        check=ConnectionPool.check_connection,  # Neon suspends idle databases; drop dead connections
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
    app.state.llm = (
        GroqClient(settings.groq_api_key, settings.groq_model) if settings.groq_api_key else None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(psycopg.errors.UndefinedTable)
    async def tables_missing(request, exc):
        return JSONResponse(
            status_code=503,
            content={"detail": "Analytics tables are not built yet. Run the pipeline first."},
        )

    @app.exception_handler(psycopg.OperationalError)
    @app.exception_handler(PoolTimeout)
    async def db_down(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.exception_handler(AskError)
    async def ask_failed(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AskUnavailable)
    async def ask_unavailable(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.get("/")
    def root():
        return {"name": "CartLens API", "docs": "/api/docs", "health": "/api/health"}

    @app.get("/api/health")
    def health(request: Request):
        llm = {
            "mode": settings.llm_mode,
            "model": settings.groq_model if settings.groq_api_key else None,
        }
        try:
            with request.app.state.pool.connection(timeout=10) as conn:
                snapshot = queries.health_snapshot(conn)
        except Exception as exc:  # health must answer even when the database is down
            return {"status": "degraded", "database": f"error: {type(exc).__name__}", "llm": llm}
        return {"status": "ok", "database": "ok", "llm": llm, **snapshot}

    @app.get("/api/v1/kpis")
    def kpis(days: int = Query(30, ge=7, le=180), conn=Depends(get_conn)):
        return queries.kpis(conn, days=days)

    @app.get("/api/v1/cities")
    def cities(limit: int = Query(10, ge=1, le=50), conn=Depends(get_conn)):
        return queries.cities(conn, limit=limit)

    @app.get("/api/v1/funnel")
    def funnel(months: int = Query(6, ge=1, le=24), conn=Depends(get_conn)):
        return queries.funnel(conn, months=months)

    @app.get("/api/v1/cohorts")
    def cohorts(months: int = Query(12, ge=1, le=24), conn=Depends(get_conn)):
        return queries.cohorts(conn, months=months)

    @app.get("/api/v1/segments")
    def segments(conn=Depends(get_conn)):
        return queries.segments(conn)

    @app.get("/api/v1/pipeline/runs")
    def pipeline_runs(limit: int = Query(20, ge=1, le=100), conn=Depends(get_conn)):
        return queries.pipeline_runs(conn, limit=limit)

    @app.get("/api/v1/ask/examples")
    def ask_examples():
        return {"mode": settings.llm_mode, "questions": [e["question"] for e in EXAMPLES]}

    @app.post("/api/v1/ask")
    def ask_question(body: AskRequest, request: Request, conn=Depends(get_conn)):
        return ask(
            body.question.strip(),
            conn=conn,
            llm=request.app.state.llm,
            max_rows=settings.ask_max_rows,
            timeout_ms=settings.ask_timeout_ms,
        )

    return app


app = create_app()
