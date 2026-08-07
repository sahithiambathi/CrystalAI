from __future__ import annotations

import csv
import functools
import json
import random
import warnings
from pathlib import Path

import numpy as np
import torch
from pymatgen.core.structure import Structure
from torch.utils.data import Dataset


def collate_pool(dataset_list):
    batch_atom_fea, batch_nbr_fea, batch_nbr_fea_idx = [], [], []
    crystal_atom_idx, batch_target = [], []
    batch_cif_ids = []
    base_idx = 0
    for (atom_fea, nbr_fea, nbr_fea_idx), target, cif_id in dataset_list:
        num_atoms = atom_fea.shape[0]
        batch_atom_fea.append(atom_fea)
        batch_nbr_fea.append(nbr_fea)
        batch_nbr_fea_idx.append(nbr_fea_idx + base_idx)
        crystal_atom_idx.append(torch.LongTensor(np.arange(num_atoms) + base_idx))
        batch_target.append(target)
        batch_cif_ids.append(cif_id)
        base_idx += num_atoms
    return (
        torch.cat(batch_atom_fea, dim=0),
        torch.cat(batch_nbr_fea, dim=0),
        torch.cat(batch_nbr_fea_idx, dim=0),
        crystal_atom_idx,
    ), torch.stack(batch_target, dim=0), batch_cif_ids


class GaussianDistance:
    def __init__(self, dmin, dmax, step, var=None):
        self.filter = np.arange(dmin, dmax + step, step)
        self.var = step if var is None else var

    def expand(self, distances):
        return np.exp(-((distances[..., np.newaxis] - self.filter) ** 2) / self.var**2)


class AtomCustomJSONInitializer:
    def __init__(self, elem_embedding_file: Path):
        with open(elem_embedding_file, encoding="utf-8") as handle:
            elem_embedding = json.load(handle)
        self.embedding = {int(key): np.asarray(value, dtype=float) for key, value in elem_embedding.items()}

    def get_atom_fea(self, atom_type: int):
        return self.embedding[atom_type]


class CrystalStructureDataset(Dataset):
    def __init__(
        self,
        csv_path: Path,
        cif_dir: Path,
        atom_init_path: Path,
        target_column: str,
        max_num_nbr: int = 12,
        radius: float = 8.0,
        dmin: float = 0.0,
        step: float = 0.2,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        self.csv_path = csv_path
        self.cif_dir = cif_dir
        self.target_column = target_column
        self.max_num_nbr = max_num_nbr
        self.radius = radius
        self.random_seed = random_seed
        self.atom_initializer = AtomCustomJSONInitializer(atom_init_path)
        self.gdf = GaussianDistance(dmin=dmin, dmax=radius, step=step)
        self.rows = self._load_rows(max_samples=max_samples)

    def _load_rows(self, max_samples: int | None):
        with open(self.csv_path, encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [row for row in reader if row.get(self.target_column) not in ("", None)]
        random.Random(self.random_seed).shuffle(rows)
        valid_rows = [row for row in rows if (self.cif_dir / f"{row['material_id']}.cif").exists()]
        if max_samples is not None:
            valid_rows = valid_rows[:max_samples]
        return valid_rows

    def __len__(self):
        return len(self.rows)

    @functools.lru_cache(maxsize=None)
    def __getitem__(self, idx: int):
        row = self.rows[idx]
        cif_id = row["material_id"]
        target = float(row[self.target_column])
        structure = Structure.from_file(self.cif_dir / f"{cif_id}.cif")
        graph = structure_to_graph(
            structure=structure,
            atom_initializer=self.atom_initializer,
            gaussian_distance=self.gdf,
            max_num_nbr=self.max_num_nbr,
            radius=self.radius,
            cif_id=cif_id,
        )
        return graph, torch.Tensor([target]), cif_id


def structure_to_graph(
    structure: Structure,
    atom_initializer: AtomCustomJSONInitializer,
    gaussian_distance: GaussianDistance,
    max_num_nbr: int = 12,
    radius: float = 8.0,
    cif_id: str = "input",
):
    atom_fea = np.vstack([atom_initializer.get_atom_fea(structure[i].specie.number) for i in range(len(structure))])
    all_nbrs = structure.get_all_neighbors(radius, include_index=True)
    all_nbrs = [sorted(nbrs, key=lambda x: x[1]) for nbrs in all_nbrs]
    nbr_fea_idx, nbr_fea = [], []

    for nbr in all_nbrs:
        if len(nbr) < max_num_nbr:
            warnings.warn(
                f"{cif_id} did not find enough neighbors to build the graph. Consider increasing the radius.",
                stacklevel=2,
            )
            nbr_fea_idx.append(list(map(lambda x: x[2], nbr)) + [0] * (max_num_nbr - len(nbr)))
            nbr_fea.append(list(map(lambda x: x[1], nbr)) + [radius + 1.0] * (max_num_nbr - len(nbr)))
        else:
            nbr_fea_idx.append(list(map(lambda x: x[2], nbr[:max_num_nbr])))
            nbr_fea.append(list(map(lambda x: x[1], nbr[:max_num_nbr])))

    nbr_fea_idx = np.asarray(nbr_fea_idx)
    nbr_fea = gaussian_distance.expand(np.asarray(nbr_fea))
    return torch.Tensor(atom_fea), torch.Tensor(nbr_fea), torch.LongTensor(nbr_fea_idx)
