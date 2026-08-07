import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers.predictions import router as predictions_router

# ML Models ready

app = FastAPI(
    title="CrystalAI Material Property Prediction API",
    version="1.0.0",
    description=(
        "Predicts material properties from Material Project IDs or CIF uploads "
        "and returns a 3D-ready crystal payload for the frontend viewer."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions_router, prefix="/api")


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
frontend_public = os.path.join(os.path.dirname(__file__), "..", "public") # If copied by Docker

# Try Docker 'public' path first, fallback to dev '../frontend/dist' path
static_dir = frontend_public if os.path.isdir(frontend_public) else frontend_dist

if os.path.isdir(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
