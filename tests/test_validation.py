from datetime import date

from validation import UserForm, parse_date_param, validate_user_form

VALID = {
    "nama": "  Siti   Aminah ",
    "alamat": "Jl. Merdeka 1",
    "no_hp": "081234567890",
    "tanggal_lahir": "2000-05-17",
    "jenis_kelamin": "Perempuan",
}


def test_valid_form_and_normalized_name():
    form = UserForm.from_mapping(VALID)
    assert form.nama == "Siti Aminah"
    assert validate_user_form(form, today=date(2025, 1, 1)) == []


def test_none_values_from_database_are_handled():
    form = UserForm.from_mapping({**VALID, "alamat": None})
    assert form.alamat == ""


def test_invalid_fields_reported():
    form = UserForm.from_mapping(
        {"nama": "Budi123", "alamat": "", "no_hp": "12ab", "tanggal_lahir": "2999-01-01", "jenis_kelamin": "X"}
    )
    errors = validate_user_form(form, today=date(2025, 1, 1))
    assert len(errors) == 5


def test_non_ascii_digits_rejected_for_phone():
    form = UserForm.from_mapping({**VALID, "no_hp": "٠٨١٢٣٤٥٦٧٨٩٠"})
    assert any("Nomor HP" in e for e in validate_user_form(form, today=date(2025, 1, 1)))


def test_parse_date_param():
    assert parse_date_param("2025-01-06") == "2025-01-06"
    assert parse_date_param("06-01-2025") is None
    assert parse_date_param(None) is None
