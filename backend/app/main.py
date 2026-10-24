from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, insights, validations
from app.core.auth import current_user
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title="Student Financial Cross-Check",
    description="Extract key fields from student financial PDFs and surface potential inconsistencies.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
auth_dependency = [Depends(current_user)]
app.include_router(documents.router, prefix=settings.api_prefix, dependencies=auth_dependency)
app.include_router(validations.router, prefix=settings.api_prefix, dependencies=auth_dependency)
app.include_router(insights.router, prefix=settings.api_prefix, dependencies=auth_dependency)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
