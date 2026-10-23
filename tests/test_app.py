import pytest

import app as app_module
from php_client import PhpApiError

USER = {
    "user_id": 1,
    "nama": "Siti Aminah",
    "alamat": "Jl. Merdeka 1",
    "no_hp": "081234567890",
    "tanggal_lahir": "2000-05-17",
    "jenis_kelamin": "Perempuan",
    "face_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
}


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.users = {USER["user_id"]: dict(USER)}
        self.deleted = []

    def get_user(self, user_id=None, face_id=None):
        return self.users.get(user_id)

    def get_all_users(self):
        return list(self.users.values())

    def register_user(self, user, face_id):
        if user["nama"] == "Siti Aminah":
            raise PhpApiError("Nama atau Face ID sudah terdaftar.", 409)
        return 2

    def update_user(self, user_id, user):
        self.users[user_id].update(user)

    def delete_user(self, user_id):
        self.deleted.append(user_id)

    def get_attendance(self, tanggal=None, user_id=None):
        return [{"absen_id": 1, "nama": "Siti Aminah", "tanggal": tanggal, "waktu_masuk": "07:55:00",
                 "status_masuk": "TEPAT WAKTU", "waktu_pulang": None, "status_pulang": None}]


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(app_module, "PhpClient", lambda *a, **k: fake)
    monkeypatch.setattr(app_module, "remove_face_data", lambda face_id: 0)
    started = []
    monkeypatch.setattr(app_module.CaptureJob, "start", lambda self, *a, **k: started.append(a) or True)
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    test_client = flask_app.test_client()
    test_client.fake = fake
    test_client.started = started
    return test_client


def test_pages_render(client):
    for url in ["/", "/register_user", "/manage_users", "/edit_user/1", "/display_attendance?tanggal=2025-01-06"]:
        assert client.get(url).status_code == 200, url


def test_register_validation_error(client):
    response = client.post("/register_user", data={**USER, "nama": "123"})
    assert response.status_code == 400
    assert client.started == []


def test_register_success_starts_capture(client):
    response = client.post("/register_user", data={**USER, "nama": "Budi Santoso"})
    assert response.status_code == 302
    assert "/users/2/capture" in response.headers["Location"]
    assert client.started[0][1] == "Budi Santoso"


def test_register_php_error_shown(client):
    response = client.post("/register_user", data=USER)
    assert response.status_code == 400
    assert "sudah terdaftar" in response.get_data(as_text=True)


def test_delete_requires_post_and_deletes(client):
    assert client.get("/delete_user/1").status_code == 405
    assert client.post("/delete_user/1").status_code == 302
    assert client.fake.deleted == [1]


def test_export_excel(client):
    response = client.get("/export_attendance_excel?tanggal=2025-01-06")
    assert response.status_code == 200
    assert response.data[:2] == b"PK"  # file xlsx = arsip zip


def test_csrf_enforced_by_default(monkeypatch):
    monkeypatch.setattr(app_module, "PhpClient", FakeClient)
    flask_app = app_module.create_app()
    assert flask_app.test_client().post("/delete_user/1").status_code == 400
