"""Olah data presensi untuk tampilan dashboard: status harian, ringkasan, dan timeline."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from attendance_rules import format_duration

DAY_NAMES = ("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min")
MONTH_NAMES = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)

STATUS_LABELS = {
    "present": "Tepat Waktu",
    "late": "Terlambat",
    "early": "Pulang Awal",
    "absent": "Tidak Hadir",
    "weekend": "Akhir Pekan",
    "upcoming": "Belum Berlangsung",
}


def parse_time(value: object) -> time | None:
    """Ubah nilai TIME dari API ('HH:MM:SS') menjadi `time`."""
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def parse_date(value: object) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_id(value: date) -> str:
    return f"{value.day} {MONTH_NAMES[value.month - 1][:3]} {value.year}"


def format_month_id(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month - 1]} {year}"


def classify_record(record: dict) -> str:
    """Status presensi satu catatan: 'late', 'early', atau 'present'."""
    if str(record.get("status_masuk") or "").startswith("TERLAMBAT"):
        return "late"
    if str(record.get("status_pulang") or "").startswith("PULANG LEBIH AWAL"):
        return "early"
    return "present"


def parse_month(value: str | None, today: date) -> tuple[int, int]:
    """Ambil (tahun, bulan) dari 'YYYY-MM'; bulan berjalan bila kosong/tidak valid."""
    if value:
        try:
            parsed = datetime.strptime(value, "%Y-%m")
            return parsed.year, parsed.month
        except ValueError:
            pass
    return today.year, today.month


def shift_month(year: int, month: int, delta: int) -> str:
    index = year * 12 + (month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass
class DayCell:
    day: date
    status: str
    record: dict | None
    is_today: bool = False

    @property
    def label(self) -> str:
        return STATUS_LABELS[self.status]


def month_calendar(year: int, month: int, records: Iterable[dict], today: date) -> list[DayCell]:
    by_date = {parse_date(r.get("tanggal")): r for r in records}
    cells = []
    for day_number in range(1, calendar.monthrange(year, month)[1] + 1):
        day = date(year, month, day_number)
        record = by_date.get(day)
        if record:
            status = classify_record(record)
        elif day.weekday() >= 5:
            status = "weekend"
        elif day >= today:
            status = "upcoming"
        else:
            status = "absent"
        cells.append(DayCell(day, status, record, is_today=day == today))
    return cells


def average_time(values: Iterable[time]) -> time | None:
    seconds = [v.hour * 3600 + v.minute * 60 + v.second for v in values]
    if not seconds:
        return None
    avg = round(sum(seconds) / len(seconds))
    return time(avg // 3600, (avg % 3600) // 60, avg % 60)


def work_duration(record: dict) -> timedelta | None:
    masuk, pulang = parse_time(record.get("waktu_masuk")), parse_time(record.get("waktu_pulang"))
    if not masuk or not pulang:
        return None
    day = date(2000, 1, 1)
    return max(datetime.combine(day, pulang) - datetime.combine(day, masuk), timedelta(0))


@dataclass
class MonthSummary:
    hadir: int
    terlambat: int
    pulang_awal: int
    tidak_hadir: int
    avg_masuk: time | None
    avg_pulang: time | None
    total_kerja: timedelta

    @property
    def total_kerja_label(self) -> str:
        return format_duration(self.total_kerja, with_seconds=False)


def summarize(cells: list[DayCell]) -> MonthSummary:
    records = [c.record for c in cells if c.record]
    durations = [d for d in (work_duration(r) for r in records) if d is not None]
    return MonthSummary(
        hadir=len(records),
        terlambat=sum(c.status == "late" for c in cells),
        pulang_awal=sum(c.status == "early" for c in cells),
        tidak_hadir=sum(c.status == "absent" for c in cells),
        avg_masuk=average_time(t for t in (parse_time(r.get("waktu_masuk")) for r in records) if t),
        avg_pulang=average_time(t for t in (parse_time(r.get("waktu_pulang")) for r in records) if t),
        total_kerja=sum(durations, timedelta(0)),
    )


@dataclass
class TimelineRow:
    day: date
    status: str
    masuk: time | None
    pulang: time | None
    start_pct: float
    width_pct: float
    duration_label: str
    open_ended: bool  # sudah masuk tetapi belum absen pulang

    @property
    def label(self) -> str:
        return STATUS_LABELS[self.status]


@dataclass
class Timeline:
    hours: list[tuple[str, float]]
    rows: list[TimelineRow]
    jam_masuk_pct: float
    jam_pulang_pct: float


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def build_timeline(records: Iterable[dict], jam_masuk: time, jam_pulang: time, now: datetime) -> Timeline:
    """Susun baris timeline (jam masuk -> jam pulang) di atas sumbu jam."""
    records = [r for r in records if parse_date(r.get("tanggal")) and parse_time(r.get("waktu_masuk"))]
    times = [parse_time(r.get(k)) for r in records for k in ("waktu_masuk", "waktu_pulang")]
    times = [t for t in times if t] + [jam_masuk, jam_pulang]

    start_hour = max(0, min(t.hour for t in times) - 1)
    end_hour = min(24, max(t.hour for t in times) + 2)
    span = (end_hour - start_hour) * 60

    def pct(minutes: int) -> float:
        return round(min(max((minutes - start_hour * 60) / span, 0), 1) * 100, 2)

    rows = []
    for record in records:
        day = parse_date(record["tanggal"])
        masuk = parse_time(record["waktu_masuk"])
        pulang = parse_time(record.get("waktu_pulang"))
        open_ended = pulang is None
        if open_ended:
            is_today = day == now.date()
            end_minutes = _minutes(now.time()) if is_today else _minutes(jam_pulang)
            duration_label = "Belum absen pulang" if is_today else "Tidak absen pulang"
        else:
            end_minutes = _minutes(pulang)
            duration_label = f"Kerja: {format_duration(work_duration(record), with_seconds=False)}"
        start = pct(_minutes(masuk))
        rows.append(
            TimelineRow(
                day=day,
                status=classify_record(record),
                masuk=masuk,
                pulang=pulang,
                start_pct=start,
                width_pct=max(pct(end_minutes) - start, 1.5),
                duration_label=duration_label,
                open_ended=open_ended,
            )
        )

    hours = [(f"{h:02d}:00", pct(h * 60)) for h in range(start_hour, end_hour + 1)]
    return Timeline(hours, rows, pct(_minutes(jam_masuk)), pct(_minutes(jam_pulang)))
