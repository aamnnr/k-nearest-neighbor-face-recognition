# Sistem Presensi Pengenalan Wajah Menggunakan K-Nearest Neighbor (KNN)

Sistem presensi yang mencatat kehadiran masuk dan pulang secara otomatis lewat pengenalan wajah. Untuk mencegah "nitip" absen, pengguna harus **berkedip** dan **tersenyum** di depan kamera sebelum presensinya dicatat. Pengguna dan rekap presensi dikelola lewat antarmuka web Flask.

> Proyek Tugas Akhir. Repository ini **tidak** menyimpan data wajah, foto, atau data pribadi apa pun. Semua data biometrik dibuat secara lokal dan sudah diabaikan oleh `.gitignore`.

## Fitur

- **Pengenalan wajah**: Haar Cascade untuk deteksi, lalu KNN (`scikit-learn`) untuk klasifikasi, ditambah ambang kemiripan *cosine* untuk menolak wajah yang tidak dikenal.
- **Verifikasi keaslian**: kedipan mata (Eye Aspect Ratio dari landmark dlib) dan senyuman (Haar Cascade).
- **Presensi masuk & pulang**:
  - Masuk sebelum/tepat `JAM_MASUK`: status **TEPAT WAKTU**.
  - Masuk setelah `JAM_MASUK`: status **TERLAMBAT (durasi)**.
  - Masuk setelah `JAM_PULANG`: ditolak.
  - Pulang sebelum `JAM_PULANG`: status **PULANG LEBIH AWAL (durasi)**. Pulang setelahnya: status **PULANG**.
- **Web Flask**: registrasi pengguna, pengambilan wajah, ambil ulang wajah, edit/hapus pengguna, rekap presensi per tanggal, dan ekspor ke Excel.
- **Notifikasi suara** (gTTS, Bahasa Indonesia).

## Arsitektur

```
Browser ──> Flask (python/app.py) ──HTTP + X-Api-Key──> API PHP (php/*.php) ──> MySQL
Kamera  ──> attendance.py ─────────HTTP + X-Api-Key──┘
             └─ dataset wajah lokal: python/data/face_dataset.npz
```

## Struktur Proyek

```
├── .env.example              # contoh konfigurasi Python (salin ke .env)
├── requirements.txt
├── php/
│   ├── config.example.php    # contoh konfigurasi DB + API key (salin ke config.local.php)
│   ├── lib/bootstrap.php     # koneksi DB, autentikasi, helper JSON & validasi
│   ├── register.php, edit_user.php, delete_user.php
│   ├── get_user_details.php, get_all_users.php
│   ├── getData.php, input.php
│   └── sql/presensi_wajah.sql
├── python/
│   ├── app.py                # web Flask
│   ├── attendance.py         # program presensi (kamera)
│   ├── add_faces.py          # ambil sampel wajah
│   ├── remove_face_data.py   # hapus sampel wajah
│   ├── recognition_preview.py# uji coba pengenalan tanpa mencatat presensi
│   ├── download_models.py    # unduh model landmark dlib
│   ├── config.py, face_store.py, recognizer.py, liveness.py,
│   │   attendance_rules.py, validation.py, php_client.py, speech.py
│   ├── templates/, static/
│   └── data/                 # model & dataset lokal (diabaikan git)
└── tests/                    # unit test (pytest)
```

## Persyaratan

- Python 3.9+ (disarankan 3.10–3.12; `dlib` butuh CMake + compiler C++ atau wheel siap pakai)
- PHP 8.0+ dan MySQL/MariaDB (mis. XAMPP)
- Webcam

## Instalasi

1. **Clone & siapkan environment Python**
   ```bash
   git clone https://github.com/aamnnr/k-nearest-neighbor-face-recognition.git
   cd k-nearest-neighbor-face-recognition
   python -m venv .venv
   .venv\Scripts\activate        # Windows  (Linux/macOS: source .venv/bin/activate)
   pip install -r requirements.txt
   ```

2. **Unduh model landmark dlib** (~100 MB, tidak disimpan di repo)
   ```bash
   python python/download_models.py
   ```
   Model ini dilatih dengan dataset iBUG 300-W yang **tidak boleh dipakai untuk tujuan komersial**.

3. **Database**: buat database `presensi_wajah`, lalu import `php/sql/presensi_wajah.sql`.

4. **API PHP**: salin folder proyek (atau buat symlink) ke `htdocs/presensi_wajah`, lalu:
   ```bash
   cp php/config.example.php php/config.local.php
   ```
   Isi kredensial database dan `api_key` dengan nilai acak:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

5. **Konfigurasi Python**:
   ```bash
   cp .env.example .env
   ```
   Isi `FLASK_SECRET_KEY` (nilai acak) dan `PHP_API_KEY` (**sama** dengan `api_key` di `config.local.php`). Sesuaikan juga `JAM_MASUK`, `JAM_PULANG`, dan `CAMERA_INDEX`.

## Penggunaan

Jalankan dari folder `python/`:

| Perintah | Fungsi |
|---|---|
| `python app.py` | Web manajemen di `http://127.0.0.1:5000` |
| `python attendance.py` | Program presensi (tekan `q` untuk keluar) |
| `python recognition_preview.py` | Uji coba pengenalan wajah tanpa mencatat presensi |
| `python add_faces.py <face_id> <nama> [--replace]` | Ambil sampel wajah secara manual |
| `python remove_face_data.py <face_id>` | Hapus sampel wajah secara manual |

Pengguna baru didaftarkan lewat web. Setelah data diri tersimpan, jendela kamera terbuka untuk mengambil sampel wajah. Mulai ulang `attendance.py` setelah menambah atau menghapus pengguna agar model dilatih ulang.

## Pengujian

```bash
pip install -r requirements-dev.txt
pytest
```

## Keamanan & Privasi

- Konfigurasi rahasia (`.env`, `php/config.local.php`) tidak ikut di-commit.
- Seluruh endpoint PHP mewajibkan header `X-Api-Key`, memakai prepared statement, dan tidak menampilkan detail error ke klien.
- Form Flask dilindungi CSRF. Mode debug mati secara default dan server hanya mendengarkan `127.0.0.1`.
- Dataset wajah disimpan sebagai `.npz` (tanpa pickle). Foto wajah mentah hanya disimpan bila `SAVE_CAPTURE_IMAGES=1`.
- Sistem ini mengolah **data biometrik**. Minta persetujuan setiap orang yang didaftarkan, dan jangan pernah meng-commit isi `python/data/` atau `python/captured_faces/`.

## Lisensi

[MIT](LICENSE)
