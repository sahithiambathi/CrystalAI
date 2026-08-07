from __future__ import annotations


def build_insights(
    band_gap_ev: float,
    formation_energy_ev_atom: float,
    formula: str,
    atom_count: int,
) -> tuple[str, list[str], list[str]]:
    material_family = _material_family(band_gap_ev)
    stability = (
        "shows strong thermodynamic stability"
        if formation_energy_ev_atom <= -1.2
        else "appears moderately stable"
        if formation_energy_ev_atom < -0.25
        else "may require synthesis care because its stability margin is limited"
    )

    summary = (
        f"{formula} behaves like a {material_family.lower()} candidate and {stability}. "
        f"The uploaded structure contains {atom_count} atomic sites in the visualized unit cell."
    )

    insights = [
        f"Estimated band gap of {band_gap_ev:.2f} eV suggests {material_family.lower()} behavior.",
        (
            f"Formation energy of {formation_energy_ev_atom:.2f} eV/atom indicates the phase "
            f"{'is energetically favorable for synthesis studies.' if formation_energy_ev_atom < 0 else 'could be metastable.'}"
        ),
        "The 3D viewer reflects the parsed unit-cell geometry from the selected CIF source.",
    ]

    applications = _applications_for_gap(band_gap_ev)
    return summary, insights, applications


def _material_family(band_gap_ev: float) -> str:
    if band_gap_ev < 0.25:
        return "Metallic"
    if band_gap_ev < 2.2:
        return "Semiconducting"
    return "Insulating"


def _applications_for_gap(band_gap_ev: float) -> list[str]:
    if band_gap_ev < 0.25:
        return [
            "Electrical contacts and conductive interconnect layers",
            "Electrode screening for energy-storage stacks",
            "Catalytic support structures where conductivity matters",
        ]
    if band_gap_ev < 2.2:
        return [
            "Photovoltaic absorber and optoelectronic screening",
            "Semiconductor device prototyping",
            "Sensors that benefit from tunable carrier transport",
        ]
    return [
        "Dielectric or insulating layers in electronic packages",
        "Protective coatings with low electronic conductivity",
        "Wide-gap optical or transparent substrate studies",
    ]
