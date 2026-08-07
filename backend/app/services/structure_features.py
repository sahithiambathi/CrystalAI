from __future__ import annotations

from math import log
from pathlib import Path

from pymatgen.core import Structure


FEATURE_NAMES = [
    "num_sites",
    "num_elements",
    "volume",
    "density",
    "volume_per_atom",
    "lattice_a",
    "lattice_b",
    "lattice_c",
    "lattice_alpha",
    "lattice_beta",
    "lattice_gamma",
    "avg_atomic_number",
    "max_atomic_number",
    "min_atomic_number",
    "avg_electronegativity",
    "electronegativity_spread",
    "avg_atomic_radius",
    "avg_row",
    "avg_group",
    "fractional_entropy",
]


def featurize_structure(structure: Structure) -> list[float]:
    composition = structure.composition
    elements = list(composition.elements)
    fractions = [composition.get_atomic_fraction(element) for element in elements]

    atomic_numbers = [float(element.Z) for element in elements]
    electronegativities = [float(element.X or 0.0) for element in elements]
    atomic_radii = [float(element.atomic_radius or 0.0) for element in elements]
    rows = [float(element.row) for element in elements]
    groups = [float(element.group or 0.0) for element in elements]

    volume = float(structure.volume)
    num_sites = float(len(structure))
    density = float(structure.density)
    lattice = structure.lattice

    return [
        num_sites,
        float(len(elements)),
        volume,
        density,
        volume / max(num_sites, 1.0),
        float(lattice.a),
        float(lattice.b),
        float(lattice.c),
        float(lattice.alpha),
        float(lattice.beta),
        float(lattice.gamma),
        _weighted_average(atomic_numbers, fractions),
        max(atomic_numbers),
        min(atomic_numbers),
        _weighted_average(electronegativities, fractions),
        max(electronegativities) - min(electronegativities),
        _weighted_average(atomic_radii, fractions),
        _weighted_average(rows, fractions),
        _weighted_average(groups, fractions),
        _fractional_entropy(fractions),
    ]


def featurize_cif_path(cif_path: Path) -> list[float]:
    structure = Structure.from_file(cif_path)
    return featurize_structure(structure)


def _weighted_average(values: list[float], weights: list[float]) -> float:
    numerator = sum(value * weight for value, weight in zip(values, weights, strict=True))
    denominator = sum(weights)
    return numerator / denominator if denominator else 0.0


def _fractional_entropy(fractions: list[float]) -> float:
    entropy = 0.0
    for fraction in fractions:
        if fraction > 0:
            entropy -= fraction * log(fraction)
    return entropy
