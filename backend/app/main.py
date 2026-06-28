from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import get_settings
from app.database import create_tables
from app.routers import (
    auth_router, assignments_router,
    submissions_router, users_router, notifications_router,
)
from app.routers import (
    auth_router,
    assignments_router,
    submissions_router,
    users_router,
    notifications_router,
)

settings = get_settings()
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating database tables…")
    await create_tables()
    logger.info("Tables ready.")

    try:
        import asyncio
        from app.services.execution_service import ensure_sandbox_image
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ensure_sandbox_image)
        logger.info("Sandbox image ready.")
    except Exception as exc:
        logger.warning("Sandbox check skipped: %s", exc)

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title       = "Lab-Grader API",
    description = "Automatic C assignment evaluation",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code = 500,
        content     = {"detail": "Internal server error"},
    )



app.include_router(auth_router,          prefix="/api/v1")
app.include_router(assignments_router,   prefix="/api/v1")
app.include_router(submissions_router,   prefix="/api/v1")
app.include_router(users_router,         prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/health/sandbox", tags=["Health"])
async def sandbox_health():
    import asyncio
    from app.services.execution_service import sandbox_health_check
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sandbox_health_check)
    return JSONResponse(
        content     = result,
        status_code = 200 if result.get("healthy") else 503,
    )