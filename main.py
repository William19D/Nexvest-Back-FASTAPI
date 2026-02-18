"""
main.py
-------
NexVest FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import historicos

app = FastAPI(
    title="NexVest API",
    description="API de análisis financiero — datos históricos de la BVC",
    version="0.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(historicos.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "NexVest API corriendo"}
