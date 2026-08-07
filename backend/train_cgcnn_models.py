from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.utils.data import DataLoader, Subset

from cgcnn.data import CrystalStructureDataset, collate_pool
from cgcnn.model import CrystalGraphConvNet


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = ROOT_DIR.parent / "data" / "materials_final.csv"
DEFAULT_CIF_DIR = ROOT_DIR.parent / "data" / "cif"
DEFAULT_ATOM_INIT_PATH = ROOT_DIR / "assets" / "atom_init.json"
DEFAULT_MODELS_DIR = ROOT_DIR / "models" / "cgcnn"


PROPERTY_CONFIG = {
    "band_gap": {"folder": "band-gap", "label": "Band gap"},
    "formation_energy": {"folder": "formation-energy-per-atom", "label": "Formation energy"},
}


@dataclass
class Normalizer:
    mean: torch.Tensor
    std: torch.Tensor

    @classmethod
    def from_targets(cls, targets: torch.Tensor) -> "Normalizer":
        mean = targets.mean(dim=0)
        std = targets.std(dim=0)
        std = torch.where(std < 1e-8, torch.ones_like(std), std)
        return cls(mean=mean, std=std)

    def norm(self, values: torch.Tensor) -> torch.Tensor:
        return (values - self.mean) / self.std

    def denorm(self, values: torch.Tensor) -> torch.Tensor:
        return values * self.std + self.mean

    def state_dict(self) -> dict[str, float]:
        return {"mean": float(self.mean.item()), "std": float(self.std.item())}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train CGCNN models for material property prediction.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--cif-dir", type=Path, default=DEFAULT_CIF_DIR)
    parser.add_argument("--atom-init-path", type=Path, default=DEFAULT_ATOM_INIT_PATH)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--max-samples", type=int, default=70000)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--atom-fea-len", type=int, default=64)
    parser.add_argument("--h-fea-len", type=int, default=128)
    parser.add_argument("--n-conv", type=int, default=4)
    parser.add_argument("--n-h", type=int, default=1)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--disable-cuda", action="store_true")
    parser.add_argument("--print-freq", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = torch.device("cpu" if args.disable_cuda or not torch.cuda.is_available() else "cuda")
    print(f"Using device: {device}")

    for property_name, config in PROPERTY_CONFIG.items():
        print(f"\n=== Training {config['label']} CGCNN ===")
        dataset = CrystalStructureDataset(
            csv_path=args.csv_path,
            cif_dir=args.cif_dir,
            atom_init_path=args.atom_init_path,
            target_column=property_name,
            max_samples=args.max_samples,
            random_seed=args.seed,
        )
        if len(dataset) < 10:
            raise RuntimeError(
                f"Dataset for {property_name} has only {len(dataset)} usable CIF rows. Check the CSV and CIF directory."
            )

        train_loader, val_loader, test_loader = build_loaders(
            dataset=dataset,
            batch_size=args.batch_size,
            workers=args.workers,
            seed=args.seed,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
        )

        sample_graph, _, _ = dataset[0]
        model = CrystalGraphConvNet(
            orig_atom_fea_len=sample_graph[0].shape[-1],
            nbr_fea_len=sample_graph[1].shape[-1],
            atom_fea_len=args.atom_fea_len,
            n_conv=args.n_conv,
            h_fea_len=args.h_fea_len,
            n_h=args.n_h,
            classification=False,
        ).to(device)
        optimizer = Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        criterion = nn.MSELoss()
        normalizer = build_normalizer(train_loader)

        output_dir = args.models_dir / config["folder"]
        output_dir.mkdir(parents=True, exist_ok=True)

        best_mae = float("inf")
        for epoch in range(1, args.epochs + 1):
            train_loss = train_one_epoch(
                loader=train_loader,
                model=model,
                criterion=criterion,
                optimizer=optimizer,
                normalizer=normalizer,
                device=device,
                print_freq=args.print_freq,
                epoch=epoch,
                label=config["label"],
            )
            val_mae = evaluate(
                loader=val_loader,
                model=model,
                criterion=criterion,
                normalizer=normalizer,
                device=device,
                label=f"{config['label']} validation",
            )
            print(
                f"Epoch {epoch:02d}/{args.epochs} | "
                f"train loss {train_loss:.4f} | val MAE {val_mae:.4f}"
            )
            checkpoint_path = output_dir / "checkpoint.pth.tar"
            bundle = {
                "epoch": epoch,
                "state_dict": model.state_dict(),
                "best_mae_error": best_mae,
                "normalizer": normalizer.state_dict(),
                "args": {
                    "atom_fea_len": args.atom_fea_len,
                    "h_fea_len": args.h_fea_len,
                    "n_conv": args.n_conv,
                    "n_h": args.n_h,
                    "task": "regression",
                },
            }
            torch.save(bundle, checkpoint_path)
            if val_mae < best_mae:
                best_mae = val_mae
                torch.save(bundle, output_dir / "model_best.pth.tar")

        best_checkpoint = torch.load(output_dir / "model_best.pth.tar", map_location=device)
        model.load_state_dict(best_checkpoint["state_dict"])
        test_mae = evaluate(
            loader=test_loader,
            model=model,
            criterion=criterion,
            normalizer=normalizer,
            device=device,
            label=f"{config['label']} test",
        )
        print(f"Saved best {config['label']} checkpoint to {output_dir / 'model_best.pth.tar'}")
        print(f"Final test MAE: {test_mae:.4f}")


def build_loaders(
    dataset: CrystalStructureDataset,
    batch_size: int,
    workers: int,
    seed: int,
    train_ratio: float,
    val_ratio: float,
):
    total = len(dataset)
    indices = list(range(total))
    random.Random(seed).shuffle(indices)

    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    train_indices = indices[:train_end]
    val_indices = indices[train_end:val_end]
    test_indices = indices[val_end:]

    if not val_indices or not test_indices:
        raise RuntimeError("Dataset split is too small. Increase sample count or adjust split ratios.")

    train_loader = DataLoader(
        Subset(dataset, train_indices),
        batch_size=batch_size,
        shuffle=True,
        num_workers=workers,
        collate_fn=collate_pool,
    )
    val_loader = DataLoader(
        Subset(dataset, val_indices),
        batch_size=batch_size,
        shuffle=False,
        num_workers=workers,
        collate_fn=collate_pool,
    )
    test_loader = DataLoader(
        Subset(dataset, test_indices),
        batch_size=batch_size,
        shuffle=False,
        num_workers=workers,
        collate_fn=collate_pool,
    )
    return train_loader, val_loader, test_loader


def build_normalizer(loader: DataLoader) -> Normalizer:
    targets = []
    for _, target, _ in loader:
        targets.append(target)
    stacked = torch.cat(targets, dim=0)
    return Normalizer.from_targets(stacked)


def move_batch(batch, device: torch.device):
    (atom_fea, nbr_fea, nbr_fea_idx, crystal_atom_idx), target, _ = batch
    atom_fea = atom_fea.to(device)
    nbr_fea = nbr_fea.to(device)
    nbr_fea_idx = nbr_fea_idx.to(device)
    crystal_atom_idx = [idx.to(device) for idx in crystal_atom_idx]
    target = target.to(device)
    return (atom_fea, nbr_fea, nbr_fea_idx, crystal_atom_idx), target


def train_one_epoch(
    loader: DataLoader,
    model: CrystalGraphConvNet,
    criterion: nn.Module,
    optimizer: Adam,
    normalizer: Normalizer,
    device: torch.device,
    print_freq: int,
    epoch: int,
    label: str,
) -> float:
    model.train()
    losses = []
    for batch_index, batch in enumerate(loader, start=1):
        inputs, target = move_batch(batch, device)
        normalized_target = normalizer.norm(target)
        prediction = model(*inputs)
        loss = criterion(prediction, normalized_target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
        if batch_index % print_freq == 0:
            print(f"{label} epoch {epoch:02d} | batch {batch_index:04d} | loss {loss.item():.4f}")
    return float(np.mean(losses))


def evaluate(
    loader: DataLoader,
    model: CrystalGraphConvNet,
    criterion: nn.Module,
    normalizer: Normalizer,
    device: torch.device,
    label: str,
) -> float:
    model.eval()
    maes = []
    losses = []
    with torch.no_grad():
        for batch in loader:
            inputs, target = move_batch(batch, device)
            normalized_target = normalizer.norm(target)
            prediction = model(*inputs)
            loss = criterion(prediction, normalized_target)
            denorm_prediction = normalizer.denorm(prediction)
            mae = torch.mean(torch.abs(denorm_prediction - target))
            losses.append(loss.item())
            maes.append(mae.item())
    mean_loss = float(np.mean(losses))
    mean_mae = float(np.mean(maes))
    print(f"{label} | loss {mean_loss:.4f} | MAE {mean_mae:.4f}")
    return mean_mae


if __name__ == "__main__":
    main()
