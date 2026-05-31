"""FastAPI application entry point."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Hellio HR API", version="2.0.0")

# CORS — dev: allow Vite dev server; configurable via env
origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


from app.routers import applications, auth, candidates, chat, ingest, positions

app.include_router(auth.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(positions.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "/app/uploads/cvs"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads/cvs", StaticFiles(directory=str(UPLOADS_DIR)), name="cv-uploads")
