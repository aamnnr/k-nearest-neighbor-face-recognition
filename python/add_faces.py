"""Ambil sampel wajah dari kamera lalu simpan ke dataset.

Penggunaan:
    python add_faces.py <face_id> <nama> [--replace]
"""

from __future__ import annotations

import argparse
import sys

import cv2
import numpy as np

import face_store
from config import CAPTURES_DIR, DATASET_PATH, settings
from recognizer import crop_face, largest_face, load_cascade, open_camera

WINDOW_NAME = "Pengambilan Data Wajah"


def safe_folder_name(name: str) -> str:
    cleaned = "".join(c for c in name if c.isalnum() or c.isspace()).strip()
    return "_".join(cleaned.split()) or "user"


def capture_faces(camera_index: int, total: int) -> list[np.ndarray]:
    detector = load_cascade("haarcascade_frontalface_default.xml")
    camera = open_camera(camera_index)
    samples: list[np.ndarray] = []
    try:
        while len(samples) < total:
            ok, frame = camera.read()
            if not ok:
                print("Gagal mengambil frame dari kamera.", file=sys.stderr)
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Hanya wajah terbesar yang diambil agar wajah orang lain di
            # latar belakang tidak ikut tersimpan dengan label pengguna ini.
            box = largest_face([tuple(f) for f in detector.detectMultiScale(gray, 1.3, 5)])
            if box is not None:
                samples.append(crop_face(frame, box))
                x, y, w, h = box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 1)

            cv2.putText(
                frame, f"Capturing: {len(samples)}/{total}", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1
            )
            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return samples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("face_id", help="ID wajah unik pengguna (UUID dari database)")
    parser.add_argument("user_name", help="Nama pengguna (untuk tampilan/nama folder)")
    parser.add_argument("--replace", action="store_true", help="Ganti sampel wajah lama milik face_id ini")
    parser.add_argument("--samples", type=int, default=settings.capture_samples, help="Jumlah sampel yang diambil")
    args = parser.parse_args(argv)

    try:
        face_id = face_store.validate_face_id(args.face_id)
        print(f"Mulai pengambilan wajah untuk {args.user_name} (Face ID: {face_id})")
        samples = capture_faces(settings.camera_index, args.samples)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not samples:
        print("Tidak ada wajah yang tertangkap. Data tidak disimpan.", file=sys.stderr)
        return 1

    total = face_store.add_samples(DATASET_PATH, face_id, np.stack(samples), replace=args.replace)

    if settings.save_capture_images:
        user_dir = CAPTURES_DIR / f"{safe_folder_name(args.user_name)}_{face_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        for i, img in enumerate(samples, start=1):
            cv2.imwrite(str(user_dir / f"{i:03d}.jpg"), img)
        print(f"Gambar wajah disimpan di {user_dir}")

    print(f"Berhasil menyimpan {len(samples)} sampel wajah untuk {args.user_name}. Total sampel dataset: {total}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
