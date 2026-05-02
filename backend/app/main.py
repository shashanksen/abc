"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.admin.admin import access_router, admin_router, modules_router
from app.admin.admin_ops import admin_ops_router
from app.auth.auth import router as auth_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.agent.router import router as agent_router, limiter
from app.modules.dq.router import router as dq_router


logger = logging.getLogger("cdp")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Don't log the DB URL (contains the password). Log just the env name.
    logger.info("[startup] env=%s", settings.app_env)
    yield
    logger.info("[shutdown]")


app = FastAPI(
    title="CDP Platform API",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─── Rate limiter (SlowAPI) ──────────────────────────────────────────────────
# Imported from app.modules.agent.router so it's the same instance used by the
# @limiter.limit decorator on the agent endpoint.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────
settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Error handler ────────────────────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.warning("[%s] %s %s — %s",
                   exc.code, request.method, request.url.path, exc.message)
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "CDP-SYS-0091",
                           "message": "Unexpected internal error",
                           "detail": str(exc)}},
    )


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(modules_router)
app.include_router(access_router)
app.include_router(admin_router)
app.include_router(admin_ops_router)
app.include_router(dq_router)
app.include_router(agent_router)
