"""Aplikasi web Flask untuk manajemen pengguna dan rekap presensi."""

from __future__ import annotations

import io
import logging
import secrets
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import date

import pandas as pd
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_wtf.csrf import CSRFProtect

from config import BASE_DIR, settings
from php_client import PhpApiError, PhpClient
from remove_face_data import remove_face_data
from validation import UserForm, parse_date_param, validate_user_form

logger = logging.getLogger(__name__)

ADD_FACES_SCRIPT = BASE_DIR / "add_faces.py"

ATTENDANCE_COLUMNS = {
    "absen_id": "ID Absen",
    "nama": "Nama",
    "tanggal": "Tanggal",
    "waktu_masuk": "Waktu Masuk",
    "status_masuk": "Status Masuk",
    "waktu_pulang": "Waktu Pulang",
    "status_pulang": "Status Pulang",
}


@dataclass
class CaptureState:
    running: bool = False
    message: str = ""
    outcome: str | None = None  # None, "success", "failure"
    face_id: str = ""
    user_name: str = ""


class CaptureJob:
    """Menjalankan add_faces.py di background; hanya satu proses dalam satu waktu."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = CaptureState()

    def snapshot(self) -> CaptureState:
        with self._lock:
            return CaptureState(**asdict(self._state))

    @property
    def running(self) -> bool:
        return self.snapshot().running

    def start(self, face_id: str, user_name: str, replace: bool = False) -> bool:
        with self._lock:
            if self._state.running:
                return False
            self._state = CaptureState(
                running=True,
                message=f"Memulai penangkapan wajah untuk {user_name}...",
                face_id=face_id,
                user_name=user_name,
            )
        threading.Thread(target=self._run, args=(face_id, user_name, replace), daemon=True).start()
        return True

    def _run(self, face_id: str, user_name: str, replace: bool) -> None:
        command = [sys.executable, str(ADD_FACES_SCRIPT), face_id, user_name]
        if replace:
            command.append("--replace")
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=BASE_DIR)
            output = (result.stdout if result.returncode == 0 else result.stderr or result.stdout).strip()
            last_line = output.splitlines()[-1] if output else ""
            outcome = "success" if result.returncode == 0 else "failure"
            message = last_line or ("Penangkapan wajah selesai." if outcome == "success" else "Penangkapan wajah gagal.")
        except OSError as exc:
            logger.exception("Gagal menjalankan add_faces.py")
            outcome, message = "failure", f"Gagal menjalankan skrip penangkapan wajah: {exc}"

        with self._lock:
            self._state.running = False
            self._state.outcome = outcome
            self._state.message = message


def create_app() -> Flask:
    app = Flask(__name__)

    secret_key = settings.flask_secret_key
    if not secret_key:
        logger.warning("FLASK_SECRET_KEY belum diatur; memakai kunci acak sementara (sesi hilang saat restart).")
        secret_key = secrets.token_hex(32)
    app.config.update(SECRET_KEY=secret_key, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    CSRFProtect(app)

    client = PhpClient(settings.php_api_base_url, settings.php_api_key, settings.http_timeout)
    capture_job = CaptureJob()

    def render_user_form(template: str, form: UserForm, **context):
        return render_template(template, form=form, today=date.today().isoformat(), **context)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register_user", methods=["GET", "POST"])
    def register_user():
        if request.method == "GET":
            return render_user_form("register_user.html", UserForm())

        form = UserForm.from_mapping(request.form)
        errors = validate_user_form(form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_user_form("register_user.html", form), 400

        if capture_job.running:
            flash("Masih ada proses penangkapan wajah yang berjalan. Tunggu hingga selesai.", "error")
            return render_user_form("register_user.html", form), 409

        face_id = str(uuid.uuid4())
        try:
            user_id = client.register_user(form.as_dict(), face_id)
        except PhpApiError as exc:
            flash(f"Gagal menyimpan data diri: {exc}", "error")
            return render_user_form("register_user.html", form), 400

        capture_job.start(face_id, form.nama)
        flash(f"Data diri {form.nama} berhasil disimpan. Silakan lihat ke kamera.", "success")
        return redirect(url_for("add_face_capture", user_id=user_id))

    @app.route("/users/<int:user_id>/capture", methods=["GET"])
    def add_face_capture(user_id: int):
        state = capture_job.snapshot()
        return render_template("add_face_capture.html", state=state, user_id=user_id)

    @app.route("/users/<int:user_id>/capture", methods=["POST"])
    def recapture_face(user_id: int):
        try:
            user = client.get_user(user_id=user_id)
        except PhpApiError as exc:
            flash(str(exc), "error")
            return redirect(url_for("manage_users"))
        if not user or not user.get("face_id"):
            abort(404)
        if not capture_job.start(user["face_id"], user["nama"], replace=True):
            flash("Masih ada proses penangkapan wajah yang berjalan. Tunggu hingga selesai.", "error")
            return redirect(url_for("manage_users"))
        return redirect(url_for("add_face_capture", user_id=user_id))

    @app.route("/status_add_face")
    def status_add_face():
        state = capture_job.snapshot()
        return jsonify(
            status=state.message,
            is_running=state.running,
            outcome=state.outcome,
            user_name=state.user_name,
        )

    @app.route("/display_attendance")
    def display_attendance():
        selected_date = parse_date_param(request.args.get("tanggal")) or date.today().isoformat()
        attendance_data: list[dict] = []
        try:
            attendance_data = client.get_attendance(tanggal=selected_date)
        except PhpApiError as exc:
            flash(f"Gagal mengambil data presensi: {exc}", "error")
        return render_template(
            "display_attendance.html", attendance_data=attendance_data, selected_date=selected_date
        )

    @app.route("/export_attendance_excel")
    def export_attendance_excel():
        selected_date = parse_date_param(request.args.get("tanggal"))
        if not selected_date:
            flash("Tanggal tidak valid.", "error")
            return redirect(url_for("display_attendance"))

        try:
            attendance_data = client.get_attendance(tanggal=selected_date)
        except PhpApiError as exc:
            flash(f"Gagal mengambil data presensi untuk ekspor: {exc}", "error")
            return redirect(url_for("display_attendance", tanggal=selected_date))

        if not attendance_data:
            flash("Tidak ada data presensi untuk diekspor pada tanggal ini.", "info")
            return redirect(url_for("display_attendance", tanggal=selected_date))

        df = pd.DataFrame(attendance_data).fillna("-")
        df = df[[col for col in ATTENDANCE_COLUMNS if col in df.columns]].rename(columns=ATTENDANCE_COLUMNS)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Presensi")
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"Rekap_Presensi_{selected_date}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.route("/manage_users")
    def manage_users():
        users: list[dict] = []
        try:
            users = client.get_all_users()
        except PhpApiError as exc:
            flash(f"Gagal mengambil data pengguna: {exc}", "error")
        return render_template("manage_users.html", users=users)

    @app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
    def edit_user(user_id: int):
        try:
            user = client.get_user(user_id=user_id)
        except PhpApiError as exc:
            flash(str(exc), "error")
            return redirect(url_for("manage_users"))
        if not user:
            flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", "error")
            return redirect(url_for("manage_users"))

        if request.method == "GET":
            return render_user_form("edit_user.html", UserForm.from_mapping(user), user_id=user_id)

        form = UserForm.from_mapping(request.form)
        errors = validate_user_form(form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_user_form("edit_user.html", form, user_id=user_id), 400

        try:
            client.update_user(user_id, form.as_dict())
        except PhpApiError as exc:
            flash(f"Gagal memperbarui data pengguna: {exc}", "error")
            return render_user_form("edit_user.html", form, user_id=user_id), 400

        flash("Data pengguna berhasil diperbarui!", "success")
        return redirect(url_for("manage_users"))

    @app.route("/delete_user/<int:user_id>", methods=["POST"])
    def delete_user(user_id: int):
        if capture_job.running:
            flash("Tidak dapat menghapus saat proses penangkapan wajah berjalan.", "error")
            return redirect(url_for("manage_users"))

        try:
            user = client.get_user(user_id=user_id)
            if not user:
                flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", "error")
                return redirect(url_for("manage_users"))
            client.delete_user(user_id)
        except PhpApiError as exc:
            flash(f"Gagal menghapus pengguna: {exc}", "error")
            return redirect(url_for("manage_users"))

        if user.get("face_id"):
            try:
                remove_face_data(user["face_id"])
            except (OSError, ValueError) as exc:
                logger.exception("Gagal menghapus data wajah %s", user["face_id"])
                flash(f"Pengguna dihapus, tetapi data wajah gagal dihapus: {exc}", "error")
                return redirect(url_for("manage_users"))

        flash("Pengguna beserta catatan presensi dan data wajahnya berhasil dihapus!", "success")
        return redirect(url_for("manage_users"))

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host=settings.flask_host, port=settings.flask_port, debug=settings.flask_debug)
