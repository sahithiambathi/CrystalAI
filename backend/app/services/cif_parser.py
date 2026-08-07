from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from pymatgen.core import Structure
from pymatgen.core.periodic_table import Element

from app.schemas.prediction import AtomPayload, BondPayload, CrystalPayload, LatticePayload


@dataclass(slots=True)
class ParsedCrystal:
    structure: Structure
    crystal: CrystalPayload


def parse_cif_file(cif_path: Path) -> ParsedCrystal:
    structure = Structure.from_file(cif_path)
    return ParsedCrystal(structure=structure, crystal=structure_to_payload(structure))


def parse_cif_text(contents: str) -> ParsedCrystal:
    with NamedTemporaryFile("w", suffix=".cif", delete=False, encoding="utf-8") as handle:
        handle.write(contents)
        temp_path = Path(handle.name)

    try:
        return parse_cif_file(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def structure_to_payload(structure: Structure) -> CrystalPayload:
    cartesian_sites = structure.cart_coords
    atoms = [
        AtomPayload(
            element=site.specie.symbol,
            atomic_number=Element(site.specie.symbol).Z,
            x=round(float(coords[0]), 4),
            y=round(float(coords[1]), 4),
            z=round(float(coords[2]), 4),
        )
        for site, coords in zip(structure, cartesian_sites, strict=True)
    ]

    bonds: list[BondPayload] = []
    neighbor_map = structure.get_neighbor_list(r=3.1)

    for center_index, neighbor_index, _, distance in zip(*neighbor_map, strict=True):
        if center_index < neighbor_index:
            bonds.append(
                BondPayload(
                    start=int(center_index),
                    end=int(neighbor_index),
                    length=round(float(distance), 4),
                )
            )

    lattice = structure.lattice

    return CrystalPayload(
        formula=structure.composition.reduced_formula,
        atom_count=len(structure),
        atoms=atoms,
        bonds=bonds,
        lattice=LatticePayload(
            matrix=[[round(float(value), 4) for value in row] for row in lattice.matrix],
            a=round(float(lattice.a), 4),
            b=round(float(lattice.b), 4),
            c=round(float(lattice.c), 4),
            alpha=round(float(lattice.alpha), 4),
            beta=round(float(lattice.beta), 4),
            gamma=round(float(lattice.gamma), 4),
            volume=round(float(lattice.volume), 4),
        ),
    )
