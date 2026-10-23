"""Verifikasi keaslian (anti "nitip" absen): deteksi kedipan mata dan senyuman."""

from __future__ import annotations

import numpy as np

LEFT_EYE = range(42, 48)
RIGHT_EYE = range(36, 42)


def eye_aspect_ratio(eye: np.ndarray) -> float:
    """Hitung Eye Aspect Ratio dari 6 titik landmark mata (urutan dlib).

    Jarak vertikal diukur antara titik tengah kelopak atas (p1, p2) dan titik
    tengah kelopak bawah (p5, p4); jarak horizontal antara sudut mata (p0, p3).
    """
    eye = np.asarray(eye, dtype=float)
    horizontal = np.linalg.norm(eye[0] - eye[3])
    if horizontal == 0:
        return 0.0
    upper_mid = (eye[1] + eye[2]) / 2
    lower_mid = (eye[5] + eye[4]) / 2
    return float(np.linalg.norm(upper_mid - lower_mid) / horizontal)


def landmarks_to_points(landmarks, indices: range) -> np.ndarray:
    return np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in indices])


class LivenessChecker:
    """Menyimpan status kedipan & senyuman sampai keduanya terpenuhi."""

    def __init__(self, ear_threshold: float = 0.2):
        self.ear_threshold = ear_threshold
        self.reset()

    def reset(self) -> None:
        self.blinked = False
        self.smiled = False
        self._eye_closed = False

    def update_eyes(self, ear: float) -> None:
        if ear < self.ear_threshold:
            self._eye_closed = True
        elif self._eye_closed:
            self.blinked = True
            self._eye_closed = False

    def mark_smile(self) -> None:
        self.smiled = True

    @property
    def passed(self) -> bool:
        return self.blinked and self.smiled
