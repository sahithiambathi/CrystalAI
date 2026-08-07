from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.cif_parser import ParsedCrystal, parse_cif_file
from app.services.material_repository import get_cif_path_for_material, material_exists_locally, normalize_material_id
from app.services.materials_project import fetch_material_from_materials_project


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ResolvedMaterial:
    material_id: str
    parsed: ParsedCrystal
    data_origin: str
    source_type: str


def resolve_material_id(material_id: str) -> ResolvedMaterial:
    normalized = normalize_material_id(material_id)

    if material_exists_locally(normalized):
        logger.info("Resolved material %s from local dataset", normalized)
        return ResolvedMaterial(
            material_id=normalized,
            parsed=parse_cif_file(get_cif_path_for_material(normalized)),
            data_origin="local dataset",
            source_type="material-id",
        )

    parsed = fetch_material_from_materials_project(normalized)
    logger.info("Resolved material %s from Materials Project API", normalized)
    return ResolvedMaterial(
        material_id=normalized,
        parsed=parsed,
        data_origin="Materials Project API",
        source_type="materials-project-api",
    )
