import asyncio

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from mangum import Mangum

from backend.app.dependencies import get_db, require_permission
from backend.app.models.user import User
from backend.app.permissions import Permission

# Import the routers 
from backend.app.routers import (
    auth_router,
    equipment_router,
    work_order_router,
    hospital_router,
    service_report_router,
    users_router,
    roles_router,
    audit_router,
)

app = FastAPI(title="MedFlow Command Center", version="1.0")

#Origin 
origins = [origin.strip() for origin in settings.frontend_origin.split(",")]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StripTrailingSlashMiddleware:
    """Lambda Function URLs strip trailing slashes; normalize every request the same way so routes match without redirects."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            if len(path) > 1 and path.endswith("/"):
                scope = dict(scope, path=path.rstrip("/"))
        await self.app(scope, receive, send)


app.add_middleware(StripTrailingSlashMiddleware)

# Attach the routers
app.include_router(auth_router)
app.include_router(equipment_router)
app.include_router(work_order_router)
app.include_router(hospital_router)
app.include_router(service_report_router)
app.include_router(users_router) # Activate the admin user creation endpoint
app.include_router(roles_router)
app.include_router(audit_router)


# --- HEALTH & UTILITY ENDPOINTS ---
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


async def _database_health(db: AsyncSession) -> str:
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=3)
    except (SQLAlchemyError, OSError, TimeoutError):
        return "unavailable"
    return "ok"


def _head_s3_bucket() -> str:
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError

        client = boto3.client(
            "s3",
            region_name=settings.aws_region_name,
            config=Config(
                connect_timeout=1,
                read_timeout=1,
                retries={"total_max_attempts": 1},
            ),
        )
        client.head_bucket(Bucket=settings.s3_bucket)
    except ImportError:
        return "unavailable"
    except (BotoCoreError, ClientError, OSError):
        return "unavailable"
    return "ok"


async def _s3_health() -> str:
    if not settings.s3_bucket:
        return "unavailable"
    try:
        return await asyncio.wait_for(asyncio.to_thread(_head_s3_bucket), timeout=3)
    except TimeoutError:
        return "unavailable"


@app.get("/health/ready", tags=["health"], response_model=None)
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    database = await _database_health(db)
    if database != "ok":
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "dependencies": {"database": database},
            },
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ready"},
    )


@app.get("/health/detail", tags=["health"])
async def health_detail(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.HEALTH_DETAIL_READ)),
) -> dict[str, object]:
    database, s3 = await asyncio.gather(_database_health(db), _s3_health())
    dependencies = {"database": database, "s3": s3}
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return {"status": status, "dependencies": dependencies}


@app.get("/version", tags=["health"])
async def version() -> dict[str, str]:
    return {"version": app.version}

# --- GLOBAL EXCEPTION HANDLERS ---
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    detail = "A database constraint was violated."
    path = request.url.path
    if path.startswith("/equipment"):
        detail = "Equipment could not be saved because a database constraint was violated."
    elif path.startswith("/users") or path.startswith("/auth"):
        detail = "User could not be saved because a database constraint was violated, such as a duplicate username."

    return JSONResponse(
        status_code=409,
        content={"detail": detail},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error has occurred."},
    )

handler = Mangum(app, lifespan="off")