"""Program presensi otomatis berbasis pengenalan wajah (KNN).

Alur: wajah dikenali -> pengguna berkedip dan tersenyum -> presensi dicatat.
Tekan 'q' untuk keluar.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime

import cv2
import dlib

import face_store
from attendance_rules import decide_attendance
from config import BACKGROUND_PATH, DATASET_PATH, SHAPE_PREDICTOR_PATH, settings
from liveness import LEFT_EYE, RIGHT_EYE, LivenessChecker, eye_aspect_ratio, landmarks_to_points
from php_client import PhpApiError, PhpClient
from recognizer import FaceRecognizer, crop_face, detect_faces, draw_label, face_to_vector, load_cascade, open_camera
from speech import speak

logger = logging.getLogger("attendance")

WINDOW_NAME = "SISTEM PRESENSI FACE RECOGNITION"
# Area pada background.png tempat frame kamera ditempelkan (x, y, lebar, tinggi)
CAMERA_SLOT = (40, 140, 640, 480)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
WHITE = (255, 255, 255)


class AttendanceApp:
    def __init__(self, client: PhpClient):
        self.client = client
        self.face_detector = load_cascade("haarcascade_frontalface_default.xml")
        self.smile_detector = load_cascade("haarcascade_smile.xml")

        if not SHAPE_PREDICTOR_PATH.exists():
            raise FileNotFoundError(
                f"{SHAPE_PREDICTOR_PATH.name} tidak ditemukan. Jalankan `python download_models.py` terlebih dahulu."
            )
        self.landmark_detector = dlib.get_frontal_face_detector()
        self.landmark_predictor = dlib.shape_predictor(str(SHAPE_PREDICTOR_PATH))

        dataset = face_store.load_dataset(DATASET_PATH)
        self.recognizer = FaceRecognizer(dataset, settings.knn_neighbors, settings.similarity_threshold)
        logger.info("Model KNN dilatih dengan %d sampel wajah.", len(dataset))

        self.background = cv2.imread(str(BACKGROUND_PATH))
        if self.background is None:
            raise FileNotFoundError(f"Gambar latar tidak dapat dimuat: {BACKGROUND_PATH}")

        self.liveness = LivenessChecker(settings.blink_ear_threshold)
        self._user_cache: dict[str, dict | None] = {}

    def lookup_user(self, face_id: str) -> dict | None:
        if face_id not in self._user_cache:
            try:
                self._user_cache[face_id] = self.client.get_user(face_id=face_id)
            except PhpApiError as exc:
                logger.error("Gagal mengambil data pengguna: %s", exc)
                return None
        return self._user_cache[face_id]

    def update_liveness(self, frame, gray) -> None:
        for rect in self.landmark_detector(gray, 0):
            landmarks = self.landmark_predictor(gray, rect)
            ear = (
                eye_aspect_ratio(landmarks_to_points(landmarks, LEFT_EYE))
                + eye_aspect_ratio(landmarks_to_points(landmarks, RIGHT_EYE))
            ) / 2
            self.liveness.update_eyes(ear)

        smiles = self.smile_detector.detectMultiScale(gray, scaleFactor=1.7, minNeighbors=50, minSize=(25, 25))
        for x, y, w, h in smiles:
            self.liveness.mark_smile()
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 1)

        for row, (label, done) in enumerate(
            (("Perlihatkan Gigi :", self.liveness.smiled), ("Pejamkan Mata :", self.liveness.blinked))
        ):
            y = 30 * (row + 1)
            cv2.putText(frame, label, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)
            cv2.putText(
                frame, " Berhasil" if done else " X", (200, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN if done else RED, 2
            )

    def recognize(self, frame, gray) -> dict | None:
        """Kenali wajah di frame. Mengembalikan data pengguna terakhir yang dikenali."""
        recognized = None
        for box in detect_faces(self.face_detector, gray):
            prediction = self.recognizer.predict(face_to_vector(crop_face(frame, box)))
            user = self.lookup_user(prediction.face_id) if prediction.face_id else None
            if user:
                recognized = user
                draw_label(frame, box, user["nama"], GREEN)
            else:
                draw_label(frame, box, "Tidak Dikenal", RED)
        return recognized

    def record(self, user: dict) -> None:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        name = user["nama"]
        try:
            records = self.client.get_attendance(tanggal=today, user_id=int(user["user_id"]))
        except PhpApiError as exc:
            logger.error("Gagal mengambil status presensi: %s", exc)
            speak("Tidak dapat terhubung ke server absen.", settings.speech_enabled)
            return

        record = records[0] if records else {}
        decision = decide_attendance(
            now,
            name,
            has_checked_in=bool(record.get("waktu_masuk")),
            has_checked_out=bool(record.get("waktu_pulang")),
            jam_masuk=settings.jam_masuk,
            jam_pulang=settings.jam_pulang,
        )
        if decision.action is None:
            speak(decision.message, settings.speech_enabled)
            return

        try:
            result = self.client.record_attendance(
                int(user["user_id"]), today, now.strftime("%H:%M:%S"), decision.action, decision.status
            )
        except PhpApiError as exc:
            logger.error("Gagal mencatat presensi: %s", exc)
            speak("Absen gagal, tolong coba lagi.", settings.speech_enabled)
            return

        if result == "berhasil":
            speak(decision.message, settings.speech_enabled)
        elif result == "sudah":
            speak(f"Maaf, {name} sudah melakukan absen {decision.action} hari ini.", settings.speech_enabled)
        elif result == "belum_masuk":
            speak(f"Maaf, {name} belum absen masuk hari ini.", settings.speech_enabled)

    def compose(self, frame):
        x, y, w, h = CAMERA_SLOT
        canvas = self.background.copy()
        canvas[y : y + h, x : x + w] = cv2.resize(frame, (w, h))
        return canvas

    def run(self) -> None:
        camera = open_camera(settings.camera_index)
        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    logger.error("Gagal mengambil frame dari kamera.")
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                self.update_liveness(frame, gray)
                user = self.recognize(frame, gray)

                cv2.imshow(WINDOW_NAME, self.compose(frame))
                key = cv2.waitKey(1) & 0xFF

                if self.liveness.passed:
                    if user:
                        self.record(user)
                    else:
                        speak("Maaf, Anda belum terdaftar!", settings.speech_enabled)
                    self.liveness.reset()

                if key == ord("q"):
                    break
        finally:
            camera.release()
            cv2.destroyAllWindows()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        client = PhpClient(settings.php_api_base_url, settings.php_api_key, settings.http_timeout)
        AttendanceApp(client).run()
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
