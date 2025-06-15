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
    * Pendaftaran pengguna baru dengan data diri (nama, alamat, no. HP, tanggal lahir) dan pengambilan data wajah.
    * Melihat daftar semua pengguna terdaftar.
    * Mengedit data diri pengguna.
    * Menghapus data pengguna (termasuk semua catatan presensi dan data wajah terkait).
* **Rekap Presensi (Melalui Web Flask):**
    * Menampilkan rekap presensi harian dalam bentuk tabel.
    * Filter data presensi berdasarkan tanggal yang dipilih secara otomatis.
    * Mengunduh data presensi harian dalam format CSV.
* **Penyimpanan Data:**
    * Data personal pengguna dan catatan presensi disimpan dalam database MySQL.
    * Data fitur wajah untuk model pengenalan disimpan dalam file `.pkl` (pickle) untuk efisiensi.
    * Rekap presensi harian juga disimpan dalam file `.csv` sebagai backup lokal.
* **Notifikasi Suara:** Memberikan umpan balik suara saat absen berhasil/gagal.
* **Tampilan Jendela OpenCV Interaktif:** Menampilkan kotak pembatas wajah dan status (dikenali/tidak dikenal) secara *real-time*.

## Struktur Proyek

├───php
│   │   delete_user.php
│   │   edit_user.php
│   │   getData.php
│   │   get_all_users.php
│   │   get_user_by_face_id.php
│   │   get_user_details.php
│   │   index.php
│   │   input.php
│   │   koneksi.php
│   │   register.php
│   │   test_koneksi.php
│   │
│   └───sql
│           presensi_wajah.sql
│
└───python
│   │   add_faces.py
│   │   app.py
│   │   background.png
│   │   remove_face_data.py
│   │   test.py
│   │
│   ├───Absen
│   ├───data
│   │       faces.pkl
│   │       haarcascade_frontalface_default.xml
│   │       haarcascade_smile.xml
│   │       names.pkl
│   │       shape_predictor_68_face_landmarks.dat
│   │
│   └───templates
│           add_face.html
│           add_face_capture.html
│           display_attendance.html
│           edit_user.html
|           index.html
|           manage_users.html
|           register_user.html
└───README.md
└───requirements.txt