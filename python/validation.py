"""Validasi data diri pengguna (dipakai saat registrasi dan edit)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping

GENDER_OPTIONS = ("Laki-laki", "Perempuan")
MAX_NAME_LENGTH = 100
MAX_ADDRESS_LENGTH = 255


@dataclass
class UserForm:
    nama: str = ""
    alamat: str = ""
    no_hp: str = ""
    tanggal_lahir: str = ""
    jenis_kelamin: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, str | None]) -> "UserForm":
        def get(key: str) -> str:
            return str(data.get(key) or "").strip()

        return cls(
            nama=" ".join(get("nama").split()),
            alamat=get("alamat"),
            no_hp=get("no_hp"),
            tanggal_lahir=get("tanggal_lahir"),
            jenis_kelamin=get("jenis_kelamin"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "nama": self.nama,
            "alamat": self.alamat,
            "no_hp": self.no_hp,
            "tanggal_lahir": self.tanggal_lahir,
            "jenis_kelamin": self.jenis_kelamin,
        }


def validate_user_form(form: UserForm, today: date | None = None) -> list[str]:
    """Kembalikan daftar pesan error; list kosong berarti data valid."""
    today = today or date.today()
    errors: list[str] = []

    if not form.nama:
        errors.append("Nama tidak boleh kosong.")
    elif len(form.nama) > MAX_NAME_LENGTH:
        errors.append(f"Nama maksimal {MAX_NAME_LENGTH} karakter.")
    elif not all(c.isalpha() or c.isspace() for c in form.nama):
        errors.append("Nama hanya boleh berisi huruf dan spasi.")

    if not form.alamat:
        errors.append("Alamat tidak boleh kosong.")
    elif len(form.alamat) > MAX_ADDRESS_LENGTH:
        errors.append(f"Alamat maksimal {MAX_ADDRESS_LENGTH} karakter.")

    if not form.no_hp:
        errors.append("Nomor HP tidak boleh kosong.")
    elif not (form.no_hp.isascii() and form.no_hp.isdigit() and 10 <= len(form.no_hp) <= 15):
        errors.append("Nomor HP harus berupa angka dan memiliki panjang antara 10 sampai 15 digit.")

    if not form.tanggal_lahir:
        errors.append("Tanggal lahir tidak boleh kosong.")
    else:
        try:
            parsed = datetime.strptime(form.tanggal_lahir, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Format tanggal lahir tidak valid.")
        else:
            if parsed > today:
                errors.append("Tanggal lahir tidak boleh di masa depan.")

    if not form.jenis_kelamin:
        errors.append("Jenis kelamin tidak boleh kosong.")
    elif form.jenis_kelamin not in GENDER_OPTIONS:
        errors.append("Pilihan jenis kelamin tidak valid.")

    return errors


def parse_date_param(value: str | None) -> str | None:
    """Kembalikan tanggal YYYY-MM-DD yang valid, atau None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None
