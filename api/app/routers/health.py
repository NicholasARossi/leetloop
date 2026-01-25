"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "LeetLoop API", "status": "running"}


@router.get("/health")
async def health_check():
    """Health check for load balancers and monitoring."""
    return {"status": "healthy", "service": "leetloop-api"}
