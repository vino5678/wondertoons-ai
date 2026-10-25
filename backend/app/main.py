import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api import characters, exports, health, jobs, projects, story
from app.core.config import Settings
from app.core.errors import AppError
from app.database.session import build_engine, build_session_factory, init_db
from app.services.jobs import fail_interrupted_jobs
from app.workers.runner import JobRunner

logging.basicConfig(level=logging.INFO)

DESCRIPTION = """
Backend for WonderToons AI Studio. Includes local mock story planning and FFmpeg video exports.
The default renderer is clearly labelled procedural 2D animation, not AI-generated video.
Errors use the shape `{"error": {"code", "message", "hint"}}` (validation errors keep FastAPI's 422 `detail` shape).
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        for d in (settings.data_dir, settings.projects_dir, settings.characters_dir, settings.temp_dir):
            d.mkdir(parents=True, exist_ok=True)
        engine = build_engine(settings.database_url)
        init_db(engine)
        app.state.engine = engine
        app.state.session_factory = build_session_factory(engine)
        with app.state.session_factory() as db:
            fail_interrupted_jobs(db)
        app.state.job_runner = JobRunner(settings.job_workers, inline=settings.run_jobs_inline)
        yield
        app.state.job_runner.shutdown()
        engine.dispose()

    app = FastAPI(title="WonderToons AI Studio API", version="0.1.0", description=DESCRIPTION,
                  docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code,
                            content={"error": {"code": exc.code, "message": exc.message, "hint": exc.hint}})

    for r in (health.router, projects.router, story.router, exports.router, characters.router, jobs.router):
        app.include_router(r)
    return app


app = create_app()
