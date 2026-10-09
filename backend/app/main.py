from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from .config import settings
from mangum import Mangum

from backend.app.database import engine
from backend.app.models.base import Base

# Import the routers 
from backend.app.routers import (
    auth_router,
    equipment_router,
    work_order_router,
    hospital_router,
    service_report_router,
    users_router
)

# Define the lifespan function BEFORE we create the app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This will drop all tables and recreate them with the correct columns!
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

# Attach the lifespan to the FastAPI app
app = FastAPI(title="MedFlow Command Center", version="1.0", lifespan=lifespan)

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

# Attach the routers
app.include_router(auth_router)
app.include_router(equipment_router)
app.include_router(work_order_router)
app.include_router(hospital_router)
app.include_router(service_report_router)
app.include_router(users_router) # Activate the admin user creation endpoint

from fastapi.routing import APIRoute

# Lambda Function URLs strip trailing slashes, so register a slash-less twin of every "/x/" route.
for route in list(app.routes):
    if isinstance(route, APIRoute) and route.path.endswith("/") and route.path != "/":
        app.add_api_route(
            route.path.rstrip("/"),
            route.endpoint,
            methods=list(route.methods),
            response_model=route.response_model,
            status_code=route.status_code,
            dependencies=route.dependencies,
            include_in_schema=False,
        )

# --- HEALTH & UTILITY ENDPOINTS ---
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

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