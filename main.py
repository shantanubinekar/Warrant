"""
Warrant — Evidence-Aware Clinical Decision Support System
FastAPI application entry point.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # must run before backend modules read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.analysis import router as analysis_router

app = FastAPI(
    title="Warrant — Clinical Decision Support",
    description=(
        "Evidence-aware clinical decision support system for the AMI domain. "
        "LLM proposes/structures/explains. Deterministic logic verifies/decides."
    ),
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(analysis_router, prefix="/api")


# Mount routes
app.include_router(analysis_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the built frontend (frontend/dist) if present — this lets the
# same service host both the API and the UI on one origin, which is the
# simplest setup for free single-service hosting (e.g. Render).
# In local dev, run the Vite dev server separately instead (npm run dev);
# this mount is a no-op until `npm run build` has been run.
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "system": "Warrant — Evidence-Aware Clinical Decision Support",
            "version": "0.1.0",
            "principle": "LLM proposes/structures/explains. Deterministic logic verifies/decides.",
            "note": "frontend/dist not found — run `npm run build` in frontend/ to serve the UI here.",
        }
