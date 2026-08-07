import os
import warnings
import pandas as pd
from mp_api.client import MPRester

# -------------------------
# 1. Setup
# -------------------------
warnings.filterwarnings("ignore")

API_KEY = os.getenv("MP_API_KEY")


if API_KEY is None:
    raise ValueError("Please set MP_API_KEY environment variable")

print("Fetching data from Materials Project...")

# -------------------------
# 2. Create folders
# -------------------------
os.makedirs("data/cif", exist_ok=True)
os.makedirs("data", exist_ok=True)

output_file = "data/materials_final.csv"

# Create CSV header once
if not os.path.exists(output_file):
    pd.DataFrame(columns=[
        "material_id",
        "formula",
        "band_gap",
        "formation_energy",
        "text"
    ]).to_csv(output_file, index=False)

# -------------------------
# 3. Fetch data
# -------------------------
with MPRester(API_KEY) as mpr:

    docs = mpr.materials.summary.search(
        fields=[
            "material_id",
            "formula_pretty",
            "band_gap",
            "formation_energy_per_atom",
            "structure"
        ],
        chunk_size=1000,
        num_chunks=70
    )

    count = 0

    for d in docs:

        # -------------------------
        # 4. Filter invalid data
        # -------------------------
        if (
            d.band_gap is None or
            d.formation_energy_per_atom is None or
            d.structure is None
        ):
            continue

        band_gap = d.band_gap
        formation_energy = d.formation_energy_per_atom
        formula = d.formula_pretty
        material_id = str(d.material_id)

        # -------------------------
        # 5. Save CIF safely
        # -------------------------
        try:
            cif_path = f"data/cif/{material_id}.cif"
            d.structure.to(filename=cif_path)
        except Exception as e:
            print(f"CIF failed for {material_id}: {e}")
            continue

        # -------------------------
        # 6. Create text modality
        # -------------------------
        if band_gap < 0.01:
            text = f"{formula} is a metallic material with high electrical conductivity."
        elif band_gap < 2:
            text = f"{formula} is a semiconductor material used in electronic devices."
        else:
            text = f"{formula} is an insulating material with low conductivity."

        # -------------------------
        # 7. Append to CSV (STREAMING)
        # -------------------------
        row = pd.DataFrame([{
            "material_id": material_id,
            "formula": formula,
            "band_gap": band_gap,
            "formation_energy": formation_energy,
            "text": text
        }])

        row.to_csv(output_file, mode="a", header=False, index=False)

        count += 1

        # progress log
        if count % 500 == 0:
            print(f"Processed {count} materials...")

# -------------------------
# 8. Done
# -------------------------
print("\nDataset creation complete!")
print(f"Saved at: {output_file}")