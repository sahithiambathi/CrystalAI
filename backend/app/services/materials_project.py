from __future__ import annotations

import logging
import os
from time import sleep

from fastapi import HTTPException
from pymatgen.core import Structure
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import MP_API_BACKOFF_SECONDS, MP_API_MAX_RETRIES, MP_API_TIMEOUT_SECONDS
from app.services.cif_parser import ParsedCrystal, structure_to_payload
from app.services.material_repository import INVALID_MATERIAL_ID_MESSAGE, cache_material_cif


logger = logging.getLogger(__name__)
MP_STRUCTURE_ENDPOINT = "https://api.materialsproject.org/materials/core/"


class TimeoutRetrySession(Session):
    def __init__(self, timeout: float):
        super().__init__()
        self._timeout = timeout

    def request(self, *args, **kwargs):  # type: ignore[override]
        kwargs.setdefault("timeout", self._timeout)
        return super().request(*args, **kwargs)


def materials_project_available() -> bool:
    return bool(_get_mp_api_key())


def fetch_material_from_materials_project(material_id: str) -> ParsedCrystal:
    api_key = _get_mp_api_key()
    if not api_key:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{material_id} was not found in the local CIF dataset. "
                "Set the MP_API_KEY environment variable to enable live Materials Project lookup."
            ),
        )

    session = _build_retry_session()
    headers = {"X-API-KEY": api_key}
    params = {
        "deprecated": "False",
        "_fields": "structure",
        "material_ids": material_id,
        "_limit": "1000",
    }

    try:
        response = session.get(MP_STRUCTURE_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        reason = str(exc).strip() or exc.__class__.__name__
        logger.warning("Materials Project lookup failed for %s: %s", material_id, reason)
        raise HTTPException(
            status_code=404,
            detail=(
                f"{material_id} was not found locally and could not be fetched from the Materials Project API. "
                f"API reason: {reason}"
            ),
        ) from exc

    data = payload.get("data") or []
    if not data:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{material_id} was not found locally and the Materials Project API returned no structure data."
            ),
        )

    structure_payload = data[0].get("structure")
    if not structure_payload:
        raise HTTPException(status_code=404, detail=INVALID_MATERIAL_ID_MESSAGE)

    try:
        structure = Structure.from_dict(structure_payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail="The Materials Project API returned structure data, but it could not be parsed.",
        ) from exc

    try:
        cache_material_cif(material_id, structure.to(fmt="cif"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not cache CIF for %s: %s", material_id, exc)

    return ParsedCrystal(structure=structure, crystal=structure_to_payload(structure))


def _build_retry_session() -> Session:
    retry = Retry(
        total=MP_API_MAX_RETRIES,
        read=MP_API_MAX_RETRIES,
        connect=MP_API_MAX_RETRIES,
        backoff_factor=MP_API_BACKOFF_SECONDS,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = TimeoutRetrySession(timeout=MP_API_TIMEOUT_SECONDS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_mp_api_key() -> str:
    return os.getenv("MP_API_KEY", "").strip()
