"""Deteksi wajah (Haar Cascade) dan pengenalan wajah (K-Nearest Neighbor)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors

from face_store import FaceDataset

FACE_SIZE = (128, 128)


def load_cascade(filename: str) -> cv2.CascadeClassifier:
    """Muat Haar Cascade bawaan paket opencv-python."""
    path = Path(cv2.data.haarcascades) / filename
    classifier = cv2.CascadeClassifier(str(path))
    if classifier.empty():
        raise FileNotFoundError(f"Haar Cascade tidak dapat dimuat: {path}")
    return classifier


def open_camera(index: int) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(index)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(
            f"Tidak dapat membuka kamera (index {index}). Pastikan kamera terhubung "
            "dan tidak dipakai aplikasi lain, atau ubah CAMERA_INDEX di .env."
        )
    return camera


def detect_faces(detector: cv2.CascadeClassifier, gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    faces = detector.detectMultiScale(
        gray, scaleFactor=1.3, minNeighbors=8, minSize=(50, 50), flags=cv2.CASCADE_SCALE_IMAGE
    )
    return [tuple(int(v) for v in face) for face in faces]


def largest_face(faces: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
    return max(faces, key=lambda f: f[2] * f[3], default=None)


def crop_face(frame: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = box
    return cv2.resize(frame[y : y + h, x : x + w], FACE_SIZE, interpolation=cv2.INTER_AREA)


def face_to_vector(face_img: np.ndarray) -> np.ndarray:
    return face_img.reshape(1, -1)


@dataclass
class Prediction:
    face_id: str | None  # None bila wajah tidak dikenali
    distance: float


class FaceRecognizer:
    """KNN untuk klasifikasi + NearestNeighbors (cosine) untuk menolak wajah asing."""

    def __init__(self, dataset: FaceDataset, n_neighbors: int = 3, threshold: float = 0.2):
        if len(dataset) == 0:
            raise ValueError("Dataset wajah kosong. Daftarkan wajah terlebih dahulu.")
        self.threshold = threshold
        self.knn = KNeighborsClassifier(n_neighbors=min(n_neighbors, len(dataset)))
        self.knn.fit(dataset.faces, dataset.labels)
        self.similarity = NearestNeighbors(n_neighbors=1, metric="cosine", algorithm="brute")
        self.similarity.fit(dataset.faces)

    def predict(self, vector: np.ndarray) -> Prediction:
        face_id = str(self.knn.predict(vector)[0])
        distances, _ = self.similarity.kneighbors(vector, n_neighbors=1)
        distance = float(distances[0][0])
        if distance >= self.threshold:
            return Prediction(None, distance)
        return Prediction(face_id, distance)


def draw_label(frame: np.ndarray, box: tuple[int, int, int, int], text: str, color: tuple[int, int, int]) -> None:
    """Gambar kotak wajah beserta label teks di atasnya."""
    x, y, w, h = box
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    (text_w, text_h), baseline = cv2.getTextSize(text, font, 0.6, 1)
    top = max(0, y - text_h - baseline - 10)
    cv2.rectangle(frame, (x, top), (x + text_w + 10, max(0, y - 5)), color, -1)
    cv2.putText(frame, text, (x + 5, max(text_h, y - baseline - 5)), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
