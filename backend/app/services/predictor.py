from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from pymatgen.core import Structure

from app.schemas.prediction import PredictionMetrics
from cgcnn.data import AtomCustomJSONInitializer, GaussianDistance, structure_to_graph
from cgcnn.model import CrystalGraphConvNet


ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models" / "cgcnn"
ATOM_INIT_PATH = ASSETS_DIR / "atom_init.json"


@dataclass
class Normalizer:
    mean: float
    std: float

    def denorm(self, value: torch.Tensor) -> torch.Tensor:
        return value * self.std + self.mean


@dataclass
class ModelBundle:
    model: CrystalGraphConvNet
    normalizer: Normalizer


class CgcnnPredictor:
    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.atom_initializer = AtomCustomJSONInitializer(ATOM_INIT_PATH)
        self.gaussian_distance = GaussianDistance(dmin=0.0, dmax=8.0, step=0.2)
        self.band_gap_bundle = self._load_bundle("band-gap")
        self.formation_energy_bundle = self._load_bundle("formation-energy-per-atom")

    def predict(self, structure: Structure) -> PredictionMetrics:
        graph = structure_to_graph(
            structure=structure,
            atom_initializer=self.atom_initializer,
            gaussian_distance=self.gaussian_distance,
            max_num_nbr=12,
            radius=8.0,
            cif_id=str(structure.composition.reduced_formula),
        )
        model_inputs = self._prepare_inputs(graph)

        band_gap = max(0.0, self._predict_single(self.band_gap_bundle, model_inputs))
        formation_energy = self._predict_single(self.formation_energy_bundle, model_inputs)
        confidence = self._estimate_confidence(structure)

        return PredictionMetrics(
            band_gap_ev=round(float(band_gap), 3),
            formation_energy_ev_atom=round(float(formation_energy), 3),
            confidence=round(float(confidence), 3),
        )

    def _load_bundle(self, model_name: str) -> ModelBundle:
        checkpoint_path = MODELS_DIR / model_name / "model_best.pth.tar"
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"Missing CGCNN checkpoint at {checkpoint_path}. Train CGCNN models before starting the backend."
            )

        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        args = checkpoint.get("args", {})
        model = CrystalGraphConvNet(
            orig_atom_fea_len=92,
            nbr_fea_len=41,
            atom_fea_len=int(args.get("atom_fea_len", 64)),
            n_conv=int(args.get("n_conv", 4)),
            h_fea_len=int(args.get("h_fea_len", 128)),
            n_h=int(args.get("n_h", 1)),
            classification=False,
        )
        model.load_state_dict(checkpoint["state_dict"])
        model.to(self.device)
        model.eval()

        normalizer_state = checkpoint.get("normalizer", {"mean": 0.0, "std": 1.0})
        return ModelBundle(
            model=model,
            normalizer=Normalizer(
                mean=float(normalizer_state["mean"]),
                std=max(float(normalizer_state["std"]), 1e-8),
            ),
        )

    def _prepare_inputs(self, graph):
        atom_fea, nbr_fea, nbr_fea_idx = graph
        atom_fea = atom_fea.to(self.device)
        nbr_fea = nbr_fea.to(self.device)
        nbr_fea_idx = nbr_fea_idx.to(self.device)
        crystal_atom_idx = [torch.arange(atom_fea.shape[0], device=self.device, dtype=torch.long)]
        return atom_fea, nbr_fea, nbr_fea_idx, crystal_atom_idx

    def _predict_single(self, bundle: ModelBundle, model_inputs) -> float:
        with torch.no_grad():
            output = bundle.model(*model_inputs).view(-1)
            prediction = bundle.normalizer.denorm(output)[0].item()
        return float(prediction)

    def _estimate_confidence(self, structure: Structure) -> float:
        num_atoms = max(len(structure), 1)
        num_elements = len(structure.composition.elements)
        complexity_penalty = min(0.22, 0.005 * num_atoms + 0.02 * max(0, num_elements - 2))
        return max(0.52, 0.9 - complexity_penalty)


_PREDICTOR: CgcnnPredictor | None = None


def predict_properties(structure: Structure) -> PredictionMetrics:
    global _PREDICTOR  # noqa: PLW0603
    if _PREDICTOR is None:
        _PREDICTOR = CgcnnPredictor()
    return _PREDICTOR.predict(structure)
