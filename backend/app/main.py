"""
AI-Assisted Office Layout Generation Platform - FastAPI Application Entry Point.
Configures CORS, global exception handlers, health endpoints, and API routers.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.persistence.database import check_db_health


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="AI-Assisted Office Layout Generation Platform API",
        description=(
            "Enterprise platform combining deterministic geometry optimization, "
            "AI intent processing, and immutable revision approval workflows."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred.", "error_type": type(exc).__name__},
        )

    # Health Check Endpoints
    @app.get("/healthz", tags=["System Health"], status_code=status.HTTP_200_OK)
    async def health_check() -> JSONResponse:
        """Liveness probe endpoint."""
        return JSONResponse(content={"status": "HEALTHY", "service": "layouts-ai-backend"})

    @app.get("/readyz", tags=["System Health"], status_code=status.HTTP_200_OK)
    async def readiness_check() -> JSONResponse:
        """Readiness probe endpoint evaluating database connectivity."""
        is_db_ready = check_db_health()
        if is_db_ready:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "READY", "database": "CONNECTED"},
            )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "NOT_READY", "database": "DISCONNECTED"},
        )

    # Include API v1 routes
    app.include_router(api_v1_router, prefix="/api")

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
