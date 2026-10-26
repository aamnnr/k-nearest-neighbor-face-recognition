"""Klien HTTP untuk API PHP (database MySQL)."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class PhpApiError(Exception):
    """Kesalahan saat berkomunikasi dengan API PHP."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PhpClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 5.0):
        if not api_key:
            raise ValueError("PHP_API_KEY belum diatur. Salin .env.example menjadi .env lalu isi nilainya.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": api_key, "Accept": "application/json"})

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            raise PhpApiError("Tidak dapat terhubung ke server PHP. Pastikan Apache/XAMPP berjalan.") from exc
        except requests.exceptions.Timeout as exc:
            raise PhpApiError("Server PHP tidak merespons (timeout).") from exc
        except requests.exceptions.RequestException as exc:
            raise PhpApiError(f"Gagal menghubungi server PHP: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            logger.error("Respons non-JSON dari %s (HTTP %s): %.200s", url, response.status_code, response.text)
            raise PhpApiError("Respons server PHP tidak valid.", response.status_code) from exc

        if not response.ok or payload.get("status") != "success":
            message = payload.get("message") or f"HTTP {response.status_code}"
            raise PhpApiError(message, response.status_code)
        return payload.get("data")

    # --- Pengguna ---------------------------------------------------------

    def get_user(self, user_id: int | None = None, face_id: str | None = None) -> dict | None:
        if user_id is not None:
            params = {"user_id": user_id}
        elif face_id:
            params = {"face_id": face_id}
        else:
            raise ValueError("user_id atau face_id wajib diisi.")
        try:
            return self._request("GET", "get_user_details.php", params=params)
        except PhpApiError as exc:
            if exc.status_code == 404:
                return None
            raise

    def get_all_users(self) -> list[dict]:
        return self._request("GET", "get_all_users.php") or []

    def register_user(self, user: dict[str, str], face_id: str) -> int:
        data = self._request("POST", "register.php", data={**user, "face_id": face_id})
        return int(data["user_id"])

    def update_user(self, user_id: int, user: dict[str, str]) -> None:
        self._request("POST", "edit_user.php", data={**user, "user_id": user_id})

    def delete_user(self, user_id: int) -> None:
        self._request("POST", "delete_user.php", data={"user_id": user_id})

    # --- Presensi ---------------------------------------------------------

    def get_attendance(
        self, tanggal: str | None = None, user_id: int | None = None, bulan: str | None = None
    ) -> list[dict]:
        """Ambil catatan presensi per tanggal (YYYY-MM-DD) atau per bulan (YYYY-MM)."""
        params: dict[str, Any] = {}
        if tanggal:
            params["tanggal"] = tanggal
        elif bulan:
            params["bulan"] = bulan
        if user_id is not None:
            params["user_id"] = user_id
        return self._request("GET", "getData.php", params=params) or []

    def record_attendance(self, user_id: int, tanggal: str, waktu: str, tipe: str, status: str) -> str:
        """Catat presensi. Mengembalikan 'berhasil', 'sudah', atau 'belum_masuk'."""
        data = self._request(
            "POST",
            "input.php",
            data={
                "user_id": user_id,
                "tanggal_absen": tanggal,
                "waktu_absen": waktu,
                "tipe_absen": tipe,
                "status": status,
            },
        )
        return data["result"]
