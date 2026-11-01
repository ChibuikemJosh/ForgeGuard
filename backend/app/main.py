"""Forge FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routers.chat import router as chat_router
from app.api.routers.graph import router as graph_router
from app.api.routers.security import router as security_router
from app.api.routers.workspace import router as workspace_router
from app.security_demo import router as security_demo_router

# Local Vite development origins. The Forge frontend runs on these origins
# during development; any additional (or production) origins must be listed
# explicitly rather than using a wide-open wildcard default.
LOCAL_FRONTEND_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


def _cors_origins() -> list[str]:
    configured = os.environ.get("FORGE_CORS_ORIGINS", "").strip()
    if configured:
        return [o.strip() for o in configured.split(",") if o.strip()]
    return LOCAL_FRONTEND_ORIGINS

app = FastAPI(title="Forge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(security_router)
app.include_router(workspace_router)
app.include_router(security_demo_router)
