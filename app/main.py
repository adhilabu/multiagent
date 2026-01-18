"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes.research import router as research_router
from app.schemas.research import HealthResponse


settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="""
## Self-Correcting Research Assistant API

A multi-agent research assistant powered by LangGraph with self-correction capabilities.

### Features
- 🔍 **Automated Research**: Breaks down queries into research steps
- 🔄 **Self-Correction**: Reviews and refines results until quality threshold
- 👤 **Human-in-the-Loop**: Optional breakpoint for human review before synthesis
- 💾 **Persistence**: Save and resume research sessions
- ⏮️ **Time-Travel Debugging**: Access checkpoints for debugging

### Workflow
1. `POST /research` - Start a new research session
2. `GET /research/{thread_id}` - Check session status
3. `POST /research/{thread_id}/approve` - Approve HITL breakpoint
4. `GET /research/{thread_id}/checkpoints` - List checkpoints
    """,
    openapi_tags=[
        {
            "name": "Research",
            "description": "Research session operations",
        },
        {
            "name": "Health",
            "description": "Health check endpoints",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research_router)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health Check",
)
async def health_check() -> HealthResponse:
    """Check if the API is running."""
    return HealthResponse(
        status="healthy",
        version=settings.version,
        app_name=settings.app_name,
    )


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API info."""
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }
