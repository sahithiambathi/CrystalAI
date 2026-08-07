from pydantic import BaseModel, Field


class AtomPayload(BaseModel):
    element: str
    atomic_number: int
    x: float
    y: float
    z: float


class BondPayload(BaseModel):
    start: int
    end: int
    length: float


class LatticePayload(BaseModel):
    matrix: list[list[float]]
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float
    volume: float


class CrystalPayload(BaseModel):
    formula: str
    atom_count: int
    atoms: list[AtomPayload]
    bonds: list[BondPayload]
    lattice: LatticePayload


class PredictionMetrics(BaseModel):
    band_gap_ev: float = Field(..., description="Estimated band gap in eV.")
    formation_energy_ev_atom: float = Field(
        ..., description="Estimated formation energy in eV/atom."
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


class PredictionResponse(BaseModel):
    source_type: str
    source_label: str
    name: str
    formula: str
    summary: str
    insights: list[str]
    applications: list[str]
    metrics: PredictionMetrics
    crystal: CrystalPayload
