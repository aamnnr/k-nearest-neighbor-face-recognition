"""Penyimpanan dataset wajah (fitur piksel + label face_id).

Dataset disimpan sebagai file `.npz` dan dibaca dengan `allow_pickle=False`,
sehingga tidak ada risiko eksekusi kode seperti pada file pickle.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")


@dataclass
class FaceDataset:
    faces: np.ndarray  # shape (N, D), dtype uint8
    labels: np.ndarray  # shape (N,), dtype str

    def __len__(self) -> int:
        return len(self.labels)

    @classmethod
    def empty(cls) -> "FaceDataset":
        return cls(faces=np.empty((0, 0), dtype=np.uint8), labels=np.empty((0,), dtype="<U64"))


def validate_face_id(face_id: str) -> str:
    """Pastikan face_id aman dipakai sebagai label maupun nama folder."""
    if not FACE_ID_PATTERN.fullmatch(face_id):
        raise ValueError(f"face_id tidak valid: {face_id!r}")
    return face_id


def load_dataset(path: Path) -> FaceDataset:
    if not path.exists():
        return FaceDataset.empty()
    with np.load(path, allow_pickle=False) as data:
        return FaceDataset(faces=data["faces"], labels=data["labels"])


def save_dataset(path: Path, dataset: FaceDataset) -> None:
    """Tulis dataset secara atomik agar file tidak rusak bila proses terhenti."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "wb") as fh:
        np.savez(fh, faces=dataset.faces, labels=dataset.labels)
    os.replace(tmp_path, path)


def add_samples(path: Path, face_id: str, samples: np.ndarray, replace: bool = False) -> int:
    """Tambahkan sampel wajah untuk `face_id`. Mengembalikan jumlah total sampel."""
    validate_face_id(face_id)
    samples = np.asarray(samples, dtype=np.uint8).reshape(len(samples), -1)
    if len(samples) == 0:
        raise ValueError("Tidak ada sampel wajah untuk disimpan.")

    dataset = load_dataset(path)
    if replace and len(dataset):
        keep = dataset.labels != face_id
        dataset = FaceDataset(faces=dataset.faces[keep], labels=dataset.labels[keep])

    new_labels = np.full(len(samples), face_id, dtype="<U64")
    if len(dataset) == 0:
        dataset = FaceDataset(faces=samples, labels=new_labels)
    else:
        if dataset.faces.shape[1] != samples.shape[1]:
            raise ValueError(
                f"Dimensi sampel ({samples.shape[1]}) berbeda dengan dataset ({dataset.faces.shape[1]})."
            )
        dataset = FaceDataset(
            faces=np.concatenate([dataset.faces, samples]),
            labels=np.concatenate([dataset.labels, new_labels]),
        )

    save_dataset(path, dataset)
    return len(dataset)


def remove_samples(path: Path, face_id: str) -> int:
    """Hapus semua sampel milik `face_id`. Mengembalikan jumlah sampel yang dihapus."""
    validate_face_id(face_id)
    dataset = load_dataset(path)
    if len(dataset) == 0:
        return 0

    keep = dataset.labels != face_id
    removed = int(len(dataset) - keep.sum())
    if removed:
        save_dataset(path, FaceDataset(faces=dataset.faces[keep], labels=dataset.labels[keep]))
    return removed
