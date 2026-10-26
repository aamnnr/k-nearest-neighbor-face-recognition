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
from datetime import date, datetime

import pandas as pd
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_wtf.csrf import CSRFProtect

import dashboard_stats as stats
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


AVATAR_COLORS = ("#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#0891b2", "#4f46e5", "#ca8a04")


def initials(name: str) -> str:
    parts = str(name or "?").split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def avatar_color(name: str) -> str:
    # Hash stabil (bukan hash() bawaan yang diacak per proses)
    return AVATAR_COLORS[sum(map(ord, str(name or ""))) % len(AVATAR_COLORS)]


def register_template_helpers(app: Flask) -> None:
    app.add_template_filter(initials, "initials")
    app.add_template_filter(avatar_color, "avatar_color")
    app.add_template_filter(stats.classify_record, "attendance_status")
    app.add_template_filter(lambda t: t.strftime("%H:%M") if t else "-", "hhmm")
    app.add_template_filter(
        lambda v: v[:5] if isinstance(v, str) and len(v) >= 5 else (v or "-"), "short_time"
    )
    app.add_template_filter(stats.format_date_id, "date_id")
    app.add_template_filter(
        lambda v: stats.format_date_id(d) if (d := stats.parse_date(v)) else (v or "-"), "date_str_id"
    )

    @app.context_processor
    def inject_globals():
        today = date.today()
        return {
            "status_labels": stats.STATUS_LABELS,
            "day_names": stats.DAY_NAMES,
            "today_label": f"{stats.DAY_NAMES[today.weekday()]}, {stats.format_date_id(today)}",
            "jam_kerja": f"{settings.jam_masuk:%H:%M} – {settings.jam_pulang:%H:%M}",
        }


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

    register_template_helpers(app)

    def render_user_form(template: str, form: UserForm, **context):
        return render_template(template, form=form, today=date.today().isoformat(), **context)

    @app.route("/")
    def index():
        today = date.today()
        users: list[dict] = []
        records: list[dict] = []
        try:
            users = client.get_all_users()
            records = client.get_attendance(tanggal=today.isoformat())
        except PhpApiError as exc:
            flash(f"Gagal memuat data dashboard: {exc}", "error")

        present_ids = {str(r.get("user_id")) for r in records}
        statuses = [stats.classify_record(r) for r in records]
        return render_template(
            "index.html",
            total_users=len(users),
            records=records,
            late_count=statuses.count("late"),
            checked_out=sum(1 for r in records if r.get("waktu_pulang")),
            absent_users=[u for u in users if str(u.get("user_id")) not in present_ids],
        )

    @app.route("/users/<int:user_id>")
    def user_detail(user_id: int):
        today = date.today()
        year, month = stats.parse_month(request.args.get("bulan"), today)
        bulan = f"{year:04d}-{month:02d}"
        try:
            user = client.get_user(user_id=user_id)
            records = client.get_attendance(user_id=user_id, bulan=bulan) if user else []
        except PhpApiError as exc:
            flash(f"Gagal memuat data pengguna: {exc}", "error")
            return redirect(url_for("manage_users"))
        if not user:
            flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", "error")
            return redirect(url_for("manage_users"))

        cells = stats.month_calendar(year, month, records, today)
        return render_template(
            "user_detail.html",
            user=user,
            bulan=bulan,
            month_label=stats.format_month_id(year, month),
            prev_month=stats.shift_month(year, month, -1),
            next_month=stats.shift_month(year, month, 1),
            cells=cells,
            summary=stats.summarize(cells),
            timeline=stats.build_timeline(records, settings.jam_masuk, settings.jam_pulang, datetime.now()),
        )

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
