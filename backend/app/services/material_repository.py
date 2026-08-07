from __future__ import annotations

import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException

from app.config import ALLOWED_MID_PREFIX, DATA_DIR, MATERIAL_SEARCH_LIMIT


MID_PATTERN = re.compile(r"^mp-\d+$", re.IGNORECASE)
MID_INPUT_PATTERN = re.compile(r"^\s*mp[-_\s]?(\d+)\s*$", re.IGNORECASE)
EXAMPLE_IDS = ["mp-1001", "mp-1003", "mp-10010"]
INVALID_MATERIAL_ID_MESSAGE = "Invalid Material ID or not found."


def normalize_material_id(material_id: str) -> str:
    match = MID_INPUT_PATTERN.match(material_id or "")
    if match is None:
        raise HTTPException(
            status_code=422,
            detail=INVALID_MATERIAL_ID_MESSAGE,
        )
    return f"{ALLOWED_MID_PREFIX}{match.group(1)}".lower()


def validate_material_id(material_id: str) -> str:
    normalized = normalize_material_id(material_id)
    if not MID_PATTERN.match(normalized):
        raise HTTPException(status_code=422, detail=INVALID_MATERIAL_ID_MESSAGE)
    return normalized


def get_cif_path_for_material(material_id: str) -> Path:
    normalized = validate_material_id(material_id)
    cif_path = DATA_DIR / f"{normalized}.cif"
    if not cif_path.exists():
        raise HTTPException(status_code=404, detail=f"No local CIF file was found for {normalized}.")
    return cif_path


def material_exists_locally(material_id: str) -> bool:
    normalized = validate_material_id(material_id)
    return (DATA_DIR / f"{normalized}.cif").exists()


def cache_material_cif(material_id: str, cif_contents: str) -> Path:
    normalized = validate_material_id(material_id)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    final_path = DATA_DIR / f"{normalized}.cif"

    if final_path.exists():
        return final_path

    with NamedTemporaryFile("w", suffix=".cif", delete=False, encoding="utf-8", dir=DATA_DIR) as handle:
        handle.write(cif_contents)
        temp_path = Path(handle.name)

    temp_path.replace(final_path)
    return final_path


def search_local_material_ids(query: str = "", limit: int = MATERIAL_SEARCH_LIMIT) -> list[str]:
    normalized_query = query.strip().lower().replace("_", "").replace(" ", "")
    matches: list[str] = []

    for cif_file in sorted(DATA_DIR.glob("mp-*.cif")):
        material_id = cif_file.stem.lower()
        comparable_material_id = material_id.replace("-", "")
        if normalized_query and normalized_query not in material_id and normalized_query not in comparable_material_id:
            continue
        matches.append(material_id)
        if len(matches) >= limit:
            break

    return matches
