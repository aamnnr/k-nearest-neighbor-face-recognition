from datetime import datetime, time, timedelta

from attendance_rules import ACTION_MASUK, ACTION_PULANG, decide_attendance, format_duration

JAM_MASUK = time(8, 0)
JAM_PULANG = time(16, 0)


def decide(now, checked_in=False, checked_out=False):
    return decide_attendance(now, "Budi", checked_in, checked_out, JAM_MASUK, JAM_PULANG)


def test_masuk_tepat_waktu():
    result = decide(datetime(2025, 1, 6, 7, 55))
    assert result.action == ACTION_MASUK
    assert result.status == "TEPAT WAKTU"


def test_masuk_terlambat_menyebut_durasi():
    result = decide(datetime(2025, 1, 6, 9, 5, 30))
    assert result.action == ACTION_MASUK
    assert result.status == "TERLAMBAT (1 jam 5 menit 30 detik)"


def test_tidak_bisa_masuk_setelah_jam_pulang():
    result = decide(datetime(2025, 1, 6, 16, 30))
    assert result.action is None


def test_pulang_lebih_awal():
    result = decide(datetime(2025, 1, 6, 14, 30), checked_in=True)
    assert result.action == ACTION_PULANG
    assert result.status == "PULANG LEBIH AWAL (1 jam 30 menit)"


def test_pulang_tepat():
    result = decide(datetime(2025, 1, 6, 16, 0), checked_in=True)
    assert result.action == ACTION_PULANG
    assert result.status == "PULANG"


def test_sudah_masuk_dan_pulang():
    result = decide(datetime(2025, 1, 6, 17, 0), checked_in=True, checked_out=True)
    assert result.action is None


def test_format_duration():
    assert format_duration(timedelta(seconds=42)) == "42 detik"
    assert format_duration(timedelta(minutes=5), with_seconds=False) == "5 menit"
    assert format_duration(timedelta(seconds=-5)) == "0 detik"
