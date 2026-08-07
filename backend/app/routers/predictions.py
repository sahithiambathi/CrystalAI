from __future__ import annotations

from anyio import to_thread
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import MAX_UPLOAD_SIZE_BYTES
from app.schemas.prediction import PredictionResponse
from app.services.cif_parser import parse_cif_text
from app.services.insights import build_insights
from app.services.material_repository import (
    EXAMPLE_IDS,
    material_exists_locally,
    search_local_material_ids,
    validate_material_id,
)
from app.services.material_resolution import resolve_material_id
from app.services.materials_project import materials_project_available
from app.services.predictor import predict_properties


router = APIRouter(tags=["predictions"])


@router.get("/examples")
def examples() -> dict[str, list[str]]:
    return {"material_ids": EXAMPLE_IDS}


@router.get("/materials/search")
def search_materials(query: str = "") -> dict[str, object]:
    return {
        "query": query,
        "material_ids": search_local_material_ids(query),
        "source": "local-dataset",
        "materials_project_enabled": materials_project_available(),
    }


@router.get("/materials/availability/{material_id}")
def material_availability(material_id: str) -> dict[str, object]:
    normalized = validate_material_id(material_id)
    local_available = material_exists_locally(normalized)
    mp_enabled = materials_project_available()
    can_predict = local_available or mp_enabled

    if local_available:
        message = f"{normalized} is available in the local CIF dataset."
    elif mp_enabled:
        message = (
            f"{normalized} is not stored locally, but live Materials Project lookup is enabled "
            "so the backend will try fetching it online."
        )
    else:
        message = (
            f"{normalized} is not in the local CIF dataset. Use one of the suggested IDs, add the "
            "matching CIF file locally, or configure MP_API_KEY to enable live Materials Project lookup."
        )

    return {
        "material_id": normalized,
        "local_available": local_available,
        "materials_project_enabled": mp_enabled,
        "can_predict": can_predict,
        "message": message,
    }


@router.get("/predict/material/{material_id}", response_model=PredictionResponse)
async def predict_from_material_id(material_id: str) -> PredictionResponse:
    resolved = await to_thread.run_sync(resolve_material_id, material_id)
    try:
        metrics = await to_thread.run_sync(predict_properties, resolved.parsed.structure)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="CGCNN checkpoints are missing. Run `python train_cgcnn_models.py` in the backend folder first.",
        ) from exc
    summary, insights, applications = build_insights(
        metrics.band_gap_ev,
        metrics.formation_energy_ev_atom,
        resolved.parsed.crystal.formula,
        resolved.parsed.crystal.atom_count,
    )
    return PredictionResponse(
        source_type=resolved.source_type,
        source_label=resolved.material_id,
        name=" ".join([e.long_name for e in resolved.parsed.structure.composition.elements]),
        formula=resolved.parsed.crystal.formula,
        summary=summary,
        insights=insights,
        applications=applications,
        metrics=metrics,
        crystal=resolved.parsed.crystal,
    )


@router.post("/predict/upload", response_model=PredictionResponse)
async def predict_from_upload(file: UploadFile = File(...)) -> PredictionResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a CIF file to continue.")
    if not file.filename.lower().endswith(".cif"):
        raise HTTPException(status_code=415, detail="Only .cif files are supported.")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="The CIF file is too large. Keep it under 5 MB.")

    try:
        parsed = parse_cif_text(contents.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="The CIF file could not be decoded as text.") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail="The CIF file could not be parsed. Please verify that it is a valid crystal structure file.",
        ) from exc

    try:
        metrics = predict_properties(parsed.structure)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="CGCNN checkpoints are missing. Run `python train_cgcnn_models.py` in the backend folder first.",
        ) from exc
    summary, insights, applications = build_insights(
        metrics.band_gap_ev,
        metrics.formation_energy_ev_atom,
        parsed.crystal.formula,
        parsed.crystal.atom_count,
    )
    return PredictionResponse(
        source_type="cif-upload",
        source_label=file.filename,
        name=" ".join([e.long_name for e in parsed.structure.composition.elements]),
        formula=parsed.crystal.formula,
        summary=summary,
        insights=insights,
        applications=applications,
        metrics=metrics,
        crystal=parsed.crystal,
    )
