"""Unduh model landmark wajah dlib (shape_predictor_68_face_landmarks.dat).

File model berukuran ~100 MB sehingga tidak disimpan di repository.
Catatan lisensi: model ini dilatih dengan dataset iBUG 300-W yang tidak
mengizinkan penggunaan komersial.
"""

from __future__ import annotations

import bz2
import sys

import requests

from config import SHAPE_PREDICTOR_PATH

MODEL_URL = "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
CHUNK_SIZE = 1 << 20


def main() -> int:
    if SHAPE_PREDICTOR_PATH.exists():
        print(f"Model sudah ada: {SHAPE_PREDICTOR_PATH}")
        return 0

    SHAPE_PREDICTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SHAPE_PREDICTOR_PATH.with_name(SHAPE_PREDICTOR_PATH.name + ".part")
    print(f"Mengunduh {MODEL_URL} ...")
    decompressor = bz2.BZ2Decompressor()
    try:
        with requests.get(MODEL_URL, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(tmp_path, "wb") as out:
                for chunk in response.iter_content(CHUNK_SIZE):
                    out.write(decompressor.decompress(chunk))
        tmp_path.replace(SHAPE_PREDICTOR_PATH)
    except (requests.RequestException, OSError, EOFError) as exc:
        tmp_path.unlink(missing_ok=True)
        print(f"Gagal mengunduh model: {exc}", file=sys.stderr)
        return 1

    print(f"Model tersimpan di {SHAPE_PREDICTOR_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
