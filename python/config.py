"""Konfigurasi aplikasi yang dibaca dari environment variable / file .env.

Semua nilai sensitif (secret key, API key) WAJIB diatur lewat environment,
tidak boleh ditulis langsung di kode. Lihat `.env.example` di root repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
CAPTURES_DIR = BASE_DIR / "captured_faces"
DATASET_PATH = DATA_DIR / "face_dataset.npz"
SHAPE_PREDICTOR_PATH = DATA_DIR / "shape_predictor_68_face_landmarks.dat"
BACKGROUND_PATH = BASE_DIR / "background.png"

try:  # python-dotenv bersifat opsional
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")


def _env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} harus berupa bilangan bulat, didapat {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = _env_str(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} harus berupa angka, didapat {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = _env_str(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_time(name: str, default: str) -> time:
    raw = _env_str(name, default)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Environment variable {name} harus berformat HH:MM atau HH:MM:SS, didapat {raw!r}")


@dataclass(frozen=True)
class Settings:
    flask_secret_key: str
    flask_debug: bool
    flask_host: str
    flask_port: int

    php_api_base_url: str
    php_api_key: str
    http_timeout: float

    camera_index: int
    capture_samples: int
    save_capture_images: bool

    knn_neighbors: int
    similarity_threshold: float
    blink_ear_threshold: float

    jam_masuk: time
    jam_pulang: time

    speech_enabled: bool


def load_settings() -> Settings:
    return Settings(
        flask_secret_key=_env_str("FLASK_SECRET_KEY"),
        flask_debug=_env_bool("FLASK_DEBUG", False),
        flask_host=_env_str("FLASK_HOST", "127.0.0.1"),
        flask_port=_env_int("FLASK_PORT", 5000),
        php_api_base_url=_env_str("PHP_API_BASE_URL", "http://localhost/presensi_wajah/php").rstrip("/"),
        php_api_key=_env_str("PHP_API_KEY"),
        http_timeout=_env_float("HTTP_TIMEOUT", 5.0),
        camera_index=_env_int("CAMERA_INDEX", 0),
        capture_samples=_env_int("CAPTURE_SAMPLES", 100),
        save_capture_images=_env_bool("SAVE_CAPTURE_IMAGES", False),
        knn_neighbors=_env_int("KNN_NEIGHBORS", 3),
        similarity_threshold=_env_float("SIMILARITY_THRESHOLD", 0.2),
        blink_ear_threshold=_env_float("BLINK_EAR_THRESHOLD", 0.2),
        jam_masuk=_env_time("JAM_MASUK", "08:00:00"),
        jam_pulang=_env_time("JAM_PULANG", "16:00:00"),
        speech_enabled=_env_bool("SPEECH_ENABLED", True),
    )


settings = load_settings()
