from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, insights, validations
from app.core.auth import current_user
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.app_env.lower() == "production":
        missing = [
            name
            for name, value in (
                ("REQUIRE_AUTH=true", settings.require_auth),
                ("SUPABASE_URL", settings.supabase_url),
                ("SUPABASE_SERVICE_KEY", settings.supabase_service_key),
                ("SUPABASE_JWT_SECRET", settings.supabase_jwt_secret),
            )
            if not value
        ]
        if not settings.allowed_origins or any(
            origin.startswith(("http://localhost", "http://127.0.0.1"))
            for origin in settings.allowed_origins
        ):
            missing.append("CORS_ORIGINS (production frontend origin)")
        if missing:
            raise RuntimeError(f"Missing required production configuration: {', '.join(missing)}")
    yield


app = FastAPI(
    title="Student Financial Cross-Check",
    description="Extract key fields from student financial PDFs and surface potential inconsistencies.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
auth_dependency = [Depends(current_user)]
app.include_router(documents.router, prefix=settings.api_prefix, dependencies=auth_dependency)
app.include_router(validations.router, prefix=settings.api_prefix, dependencies=auth_dependency)
app.include_router(insights.router, prefix=settings.api_prefix, dependencies=auth_dependency)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
