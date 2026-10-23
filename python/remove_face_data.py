"""Hapus data wajah milik satu pengguna dari dataset (dan folder foto bila ada).

Penggunaan:
    python remove_face_data.py <face_id>
"""

from __future__ import annotations

import argparse
import shutil
import sys

import face_store
from config import CAPTURES_DIR, DATASET_PATH


def remove_face_data(face_id: str) -> int:
    """Hapus sampel dataset dan folder foto milik `face_id`. Mengembalikan jumlah sampel terhapus."""
    face_store.validate_face_id(face_id)
    removed = face_store.remove_samples(DATASET_PATH, face_id)
    if CAPTURES_DIR.is_dir():
        for folder in CAPTURES_DIR.glob(f"*_{face_id}"):
            if folder.is_dir():
                shutil.rmtree(folder)
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("face_id")
    args = parser.parse_args(argv)
    try:
        removed = remove_face_data(args.face_id)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"{removed} sampel wajah untuk Face ID {args.face_id} dihapus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
