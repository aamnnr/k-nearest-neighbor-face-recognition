from datetime import date, datetime, time, timedelta

import dashboard_stats as stats


def record(tanggal, masuk="07:50:00", pulang="16:10:00", status_masuk="TEPAT WAKTU", status_pulang="PULANG"):
    return {
        "tanggal": tanggal,
        "waktu_masuk": masuk,
        "waktu_pulang": pulang,
        "status_masuk": status_masuk,
        "status_pulang": status_pulang,
    }


def test_classify_record():
    assert stats.classify_record(record("2025-01-06")) == "present"
    assert stats.classify_record(record("2025-01-06", status_masuk="TERLAMBAT (5 menit)")) == "late"
    assert stats.classify_record(record("2025-01-06", status_pulang="PULANG LEBIH AWAL (1 jam)")) == "early"


def test_month_calendar_statuses():
    # Januari 2025: tanggal 4-5 Sabtu-Minggu, "hari ini" tanggal 8
    records = [record("2025-01-02"), record("2025-01-03", status_masuk="TERLAMBAT (1 menit)")]
    cells = stats.month_calendar(2025, 1, records, today=date(2025, 1, 8))
    by_day = {c.day.day: c.status for c in cells}

    assert len(cells) == 31
    assert by_day[2] == "present"
    assert by_day[3] == "late"
    assert by_day[4] == by_day[5] == "weekend"
    assert by_day[6] == "absent"
    assert by_day[8] == "upcoming" and cells[7].is_today
    assert by_day[20] == "upcoming"


def test_summarize():
    records = [record("2025-01-02", "07:00:00", "15:00:00"), record("2025-01-03", "08:00:00", "16:30:00")]
    summary = stats.summarize(stats.month_calendar(2025, 1, records, today=date(2025, 1, 4)))
    assert summary.hadir == 2
    assert summary.avg_masuk == time(7, 30)
    assert summary.avg_pulang == time(15, 45)
    assert summary.total_kerja == timedelta(hours=16, minutes=30)
    assert summary.tidak_hadir == 1  # tanggal 1 (Rabu)


def test_parse_and_shift_month():
    today = date(2025, 3, 10)
    assert stats.parse_month("2024-12", today) == (2024, 12)
    assert stats.parse_month("salah", today) == (2025, 3)
    assert stats.shift_month(2025, 1, -1) == "2024-12"
    assert stats.shift_month(2024, 12, 1) == "2025-01"


def test_build_timeline_positions():
    now = datetime(2025, 1, 6, 12, 0)
    records = [record("2025-01-03", "08:00:00", "16:00:00"), record("2025-01-06", "08:00:00", None)]
    timeline = stats.build_timeline(records, time(8), time(16), now)

    assert timeline.hours[0][0] == "07:00" and timeline.hours[-1][0] == "18:00"
    full, open_row = timeline.rows
    assert 0 < full.start_pct < full.start_pct + full.width_pct <= 100
    assert full.duration_label == "Kerja: 8 jam 0 menit"
    assert open_row.open_ended and open_row.duration_label == "Belum absen pulang"
    assert timeline.jam_masuk_pct < timeline.jam_pulang_pct


def test_build_timeline_ignores_incomplete_records():
    timeline = stats.build_timeline([{"tanggal": "2025-01-06"}], time(8), time(16), datetime(2025, 1, 6))
    assert timeline.rows == []
