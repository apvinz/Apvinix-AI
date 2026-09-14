import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="TRANSCORE AI",
    description="Turn sound into notation. AI-generated transcription designed to "
    "preserve the musical structure and performance as accurately as possible.",
    version="0.1.0-mvp",
)

# Default dev origins + any extra origins from env (comma-separated), e.g.
# TRANSCORE_CORS_ORIGINS="https://your-app.netlify.app,https://your-custom-domain.com"
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra_origins = [
    o.strip() for o in os.environ.get("TRANSCORE_CORS_ORIGINS", "").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "product": "TRANSCORE AI"}
