"""Uji coba pengenalan wajah tanpa mencatat presensi (menampilkan jarak & waktu proses).

Tekan 'q' untuk keluar.
"""

from __future__ import annotations

import sys
import time

import cv2

import face_store
from config import DATASET_PATH, settings
from php_client import PhpApiError, PhpClient
from recognizer import FaceRecognizer, crop_face, detect_faces, draw_label, face_to_vector, load_cascade, open_camera

WINDOW_NAME = "Uji Coba Pengenalan Wajah"


def main() -> int:
    try:
        client = PhpClient(settings.php_api_base_url, settings.php_api_key, settings.http_timeout)
        detector = load_cascade("haarcascade_frontalface_default.xml")
        recognizer = FaceRecognizer(
            face_store.load_dataset(DATASET_PATH), settings.knn_neighbors, settings.similarity_threshold
        )
        camera = open_camera(settings.camera_index)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    names: dict[str, str] = {}
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Gagal mengambil frame dari kamera.", file=sys.stderr)
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            for box in detect_faces(detector, gray):
                start = time.perf_counter()
                prediction = recognizer.predict(face_to_vector(crop_face(frame, box)))
                if prediction.face_id and prediction.face_id not in names:
                    try:
                        user = client.get_user(face_id=prediction.face_id)
                    except PhpApiError as exc:
                        print(f"Gagal mengambil data pengguna: {exc}", file=sys.stderr)
                        user = None
                    names[prediction.face_id] = user["nama"] if user else f"ID {prediction.face_id}"
                elapsed = time.perf_counter() - start

                if prediction.face_id:
                    text, color = f"Dikenal: {names[prediction.face_id]}", (0, 255, 0)
                else:
                    text, color = "Tidak Dikenal", (0, 0, 255)
                text = f"{text} ({elapsed:.2f}s)"
                print(f"{text} jarak={prediction.distance:.4f}")
                draw_label(frame, box, text, color)

            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
