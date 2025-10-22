# Sistem Presensi Pengenalan Wajah Berbasis IoT Menggunakan Metode K-Nearest Neighbor (KNN)

Sistem presensi ini memanfaatkan teknologi pengenalan wajah untuk mencatat kehadiran masuk dan pulang karyawan/mahasiswa secara otomatis. Dilengkapi dengan deteksi kedipan mata dan senyuman untuk mencegah "nitip" absen, serta antarmuka web sederhana berbasis Flask untuk manajemen pengguna dan rekap presensi.

## Fitur Utama

* **Pengenalan Wajah Otomatis:** Mendeteksi dan mengenali wajah individu menggunakan model machine learning (KNN).
* **Verifikasi Keaslian:** Deteksi kedipan mata dan senyuman untuk memastikan keberadaan fisik pengguna saat absen.
* **Absen Masuk & Pulang:**
    * Absen masuk: Dilakukan sebelum jam masuk.
    * Absen terlambat: Jika absen masuk dilakukan 15 menit setelah jam masuk.
    * Tidak bisa absen masuk: Jika terlambat lebih dari 15 menit.
    * Absen pulang: Dilakukan saat atau setelah jam pulang.
* **Manajemen Pengguna (Melalui Web Flask):**
    * Pendaftaran pengguna baru dengan data diri (nama, alamat, no. HP, tanggal lahir, jenis kelamin) dan pengambilan data wajah.
    * Melihat daftar semua pengguna terdaftar.
    * Mengedit data diri pengguna.
    * Menghapus data pengguna (termasuk semua catatan presensi dan data wajah terkait).
* **Rekap Presensi (Melalui Web Flask):**
    * Menampilkan rekap presensi harian dalam bentuk tabel.
    * Filter data presensi berdasarkan tanggal yang dipilih secara otomatis.
    * Mengunduh data presensi harian dalam format Excel (.xlsx).
* **Penyimpanan Data:**
    * Data personal pengguna dan catatan presensi disimpan dalam database MySQL.
    * Data fitur wajah untuk model pengenalan disimpan dalam file `.pkl` (pickle) untuk efisiensi.
    * Rekap presensi harian juga disimpan dalam file `.csv` sebagai backup lokal.
* **Notifikasi Suara:** Memberikan umpan balik suara saat absen berhasil/gagal.
* **Tampilan Jendela OpenCV Interaktif:** Menampilkan kotak pembatas wajah dan status (dikenali/tidak dikenal) secara *real-time*.

## Persyaratan Sistem

* Python 3.7+
* MySQL/MariaDB
* Webcam atau kamera yang terhubung
* XAMPP (untuk server PHP dan MySQL)

## Instalasi

1. **Clone Repository:**
   ```bash
   git clone <repository-url>
   cd Sistem-Presensi-Pengenalan-Wajah-KNN
   ```

2. **Setup Database:**
   - Jalankan XAMPP dan pastikan MySQL aktif.
   - Buat database baru bernama `presensi_wajah`.
   - Import file `php/sql/presensi_wajah.sql` ke database tersebut.

3. **Setup Python Environment:**
   - Buat virtual environment (opsional tapi direkomendasikan):
     ```bash
     python -m venv venv
     venv\Scripts\activate  # Pada Windows
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

4. **Konfigurasi:**
   - Pastikan file-file model (seperti `haarcascade_frontalface_default.xml`, `shape_predictor_68_face_landmarks.dat`) ada di folder `python/data/`.
   - Sesuaikan konfigurasi database di `php/koneksi.php` jika diperlukan.

## Penggunaan

1. **Jalankan Server PHP:**
   - Pastikan XAMPP berjalan dan Apache aktif.
   - Akses aplikasi web melalui browser di `http://localhost/presensi_wajah/php/index.php` (opsional).

2. **Jalankan Aplikasi Flask:**
   - Dari folder `python`, jalankan:
     ```bash
     python app.py
     ```
   - Akses web interface di `http://localhost:5000`.

3. **Manajemen Pengguna:**
   - Daftar pengguna baru melalui web interface.
   - Jalankan `python add_faces.py <face_id> <user_name>` untuk menangkap data wajah.

4. **Presensi:**
   - Jalankan `python test.py` untuk memulai sistem presensi otomatis.
   - Sistem akan mendeteksi wajah, memverifikasi dengan kedipan mata dan senyuman, lalu mencatat absen.

## Struktur Proyek

```
├── README.md
├── requirements.txt
├── php/
│   ├── delete_user.php
│   ├── edit_user.php
│   ├── get_all_users.php
│   ├── get_user_by_face_id.php
│   ├── get_user_details.php
│   ├── getData.php
│   ├── index.php
│   ├── input.php
│   ├── koneksi.php
│   ├── register.php
│   └── sql/
│       └── presensi_wajah.sql
└── python/
    ├── Absen/
    ├── add_faces.py
    ├── app.py
    ├── background.png
    ├── data/
    │   ├── faces.pkl
    │   ├── haarcascade_frontalface_default.xml
    │   ├── haarcascade_smile.xml
    │   ├── names.pkl
    │   └── shape_predictor_68_face_landmarks.dat
    ├── remove_face_data.py
    ├── templates/
    │   ├── add_face.html
    │   ├── add_face_capture.html
    │   ├── display_attendance.html
    │   ├── edit_user.html
    │   ├── index.html
    │   ├── manage_users.html
    │   └── register_user.html
    └── test.py
```

## Kontribusi

Kontribusi sangat diterima! Silakan buat issue atau pull request untuk perbaikan dan fitur baru.

## Lisensi

Proyek ini menggunakan lisensi MIT. Lihat file LICENSE untuk detail lebih lanjut.
