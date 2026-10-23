"""Aturan bisnis presensi masuk/pulang (murni, tanpa kamera maupun jaringan)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

ACTION_MASUK = "masuk"
ACTION_PULANG = "pulang"


@dataclass(frozen=True)
class AttendanceDecision:
    action: str | None  # "masuk", "pulang", atau None bila tidak ada yang dicatat
    status: str  # status yang disimpan ke database
    message: str  # pesan yang diucapkan ke pengguna


def format_duration(delta: timedelta, with_seconds: bool = True) -> str:
    total = max(int(delta.total_seconds()), 0)
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)

    parts = []
    if hours:
        parts.append(f"{hours} jam")
    if minutes or not with_seconds:
        parts.append(f"{minutes} menit")
    if with_seconds:
        parts.append(f"{seconds} detik")
    return " ".join(parts)


def decide_attendance(
    now: datetime,
    name: str,
    has_checked_in: bool,
    has_checked_out: bool,
    jam_masuk: time,
    jam_pulang: time,
) -> AttendanceDecision:
    target_masuk = datetime.combine(now.date(), jam_masuk)
    target_pulang = datetime.combine(now.date(), jam_pulang)

    if not has_checked_in:
        if now.time() > jam_pulang:
            return AttendanceDecision(
                None, "", f"Maaf, {name}, Anda tidak bisa absen masuk karena sudah melewati jam pulang hari ini."
            )
        if now <= target_masuk:
            return AttendanceDecision(
                ACTION_MASUK, "TEPAT WAKTU", f"Halo {name}, Absen Masuk Tepat Waktu! Selamat datang!"
            )
        late = format_duration(now - target_masuk)
        return AttendanceDecision(
            ACTION_MASUK, f"TERLAMBAT ({late})", f"Halo {name}, Anda Absen Masuk Terlambat {late}."
        )

    if not has_checked_out:
        if now >= target_pulang:
            return AttendanceDecision(
                ACTION_PULANG, "PULANG", f"Terima kasih {name}, Absen Pulang Berhasil! Sampai jumpa besok."
            )
        early = format_duration(target_pulang - now, with_seconds=False)
        return AttendanceDecision(
            ACTION_PULANG, f"PULANG LEBIH AWAL ({early})", f"Maaf, {name} Absen Pulang Lebih Awal {early}."
        )

    return AttendanceDecision(None, "", f"Maaf, {name} sudah melakukan absen masuk dan pulang hari ini.")
