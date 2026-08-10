from __future__ import annotations

import logging
import os

from fastapi import HTTPException
from mp_api.client import MPRester
from pymatgen.core import Structure

from app.services.cif_parser import ParsedCrystal, structure_to_payload
from app.services.material_repository import (
    INVALID_MATERIAL_ID_MESSAGE,
    cache_material_cif,
)

logger = logging.getLogger(__name__)


def materials_project_available() -> bool:
    return bool(_get_mp_api_key())


def fetch_material_from_materials_project(material_id: str) -> ParsedCrystal:
    api_key = _get_mp_api_key()

    if not api_key:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{material_id} was not found in the local CIF dataset. "
                "Set the MP_API_KEY environment variable to enable live "
                "Materials Project lookup."
            ),
        )

    try:
        with MPRester(api_key) as mpr:
            results = mpr.materials.summary.search(
                material_ids=[material_id],
                fields=["structure"],
            )

        if not results:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{material_id} was not found locally and the "
                    "Materials Project API returned no structure data."
                ),
            )

        structure = results[0].structure

        if structure is None:
            raise HTTPException(
                status_code=404,
                detail=INVALID_MATERIAL_ID_MESSAGE,
            )

    except HTTPException:
        raise
    except Exception as exc:
        reason = str(exc).strip() or exc.__class__.__name__

        logger.warning(
            "Materials Project lookup failed for %s: %s",
            material_id,
            reason,
        )

        raise HTTPException(
            status_code=404,
            detail=(
                f"{material_id} was not found locally and could not be "
                f"fetched from the Materials Project API. "
                f"API reason: {reason}"
            ),
        ) from exc

    try:
        cache_material_cif(
            material_id,
            structure.to(fmt="cif"),
        )
    except Exception as exc:
        logger.warning(
            "Could not cache CIF for %s: %s",
            material_id,
            exc,
        )

    return ParsedCrystal(
        structure=structure,
        crystal=structure_to_payload(structure),
    )


def _get_mp_api_key() -> str:
    return os.getenv("MP_API_KEY", "").strip()