<?php
include 'koneksi.php'; // Pastikan file koneksi.php ada dan berfungsi

// Aktifkan pelaporan error untuk debugging (Hapus di produksi!)
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Set header untuk memastikan respons adalah plain text
header('Content-Type: text/plain');

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    // Ambil data dari POST request, gunakan operator null coalescing (??) untuk menghindari undefined index
    $nama = $_POST['nama'] ?? '';
    $alamat = $_POST['alamat'] ?? '';
    $no_hp = $_POST['no_hp'] ?? '';
    $tanggal_lahir = $_POST['tanggal_lahir'] ?? '';
    $jenis_kelamin = $_POST['jenis_kelamin'] ?? '';
    $face_id = $_POST['face_id'] ?? '';

    // Cek koneksi database
    if ($conn->connect_error) {
        echo "gagal: Error koneksi database: " . $conn->connect_error;
        exit();
    }

    // =====================================================================
    // Validasi Sisi Server di PHP (Wajib Diisi & Format)
    // =====================================================================
    if (empty($nama)) {
        echo "gagal: Nama tidak boleh kosong.";
        exit();
    }
    // Validasi Nama: hanya huruf dan spasi
    if (!preg_match("/^[A-Za-z\s]+$/", $nama)) {
        echo "gagal: Nama hanya boleh berisi huruf dan spasi.";
        exit();
    }

    if (empty($alamat)) { // Validasi wajib isi alamat
        echo "gagal: Alamat tidak boleh kosong.";
        exit();
    }

    if (empty($no_hp)) { // Validasi wajib isi nomor HP
        echo "gagal: Nomor HP tidak boleh kosong.";
        exit();
    }
    // Validasi Nomor HP: hanya angka dan panjang 10-15 (sesuaikan dengan pattern di HTML dan Flask)
    if (!preg_match("/^[0-9]{10,15}$/", $no_hp)) {
        echo "gagal: Format nomor HP tidak valid (10-15 digit angka).";
        exit();
    }

    if (empty($tanggal_lahir)) { // Validasi wajib isi tanggal lahir
        echo "gagal: Tanggal lahir tidak boleh kosong.";
        exit();
    }
    // Cek apakah tanggal valid dan tidak di masa depan
    try {
        $date_obj = new DateTime($tanggal_lahir);
        $today = new DateTime();
        if ($date_obj > $today) {
            echo "gagal: Tanggal lahir tidak boleh di masa depan.";
            exit();
        }
    } catch (Exception $e) {
        echo "gagal: Format tanggal lahir tidak valid.";
        exit();
    }
    
    if (empty($jenis_kelamin)) { // Validasi wajib isi jenis kelamin
        echo "gagal: Jenis kelamin tidak boleh kosong.";
        exit();
    }
    // Validasi Jenis Kelamin: harus 'Laki-laki' atau 'Perempuan'
    if (!in_array($jenis_kelamin, ['Laki-laki', 'Perempuan'])) {
        echo "gagal: Pilihan jenis kelamin tidak valid.";
        exit();
    }

    if (empty($face_id)) {
        echo "gagal: Face ID tidak boleh kosong.";
        exit();
    }

    // Cek apakah nama atau face_id sudah terdaftar
    $stmt_check = $conn->prepare("SELECT user_id FROM users WHERE nama = ? OR face_id = ?");
    if ($stmt_check === false) {
        echo "gagal: Prepare statement check failed: " . $conn->error;
        $conn->close();
        exit();
    }
    $stmt_check->bind_param("ss", $nama, $face_id);
    $stmt_check->execute();
    $stmt_check->store_result();

    if ($stmt_check->num_rows > 0) {
        echo "gagal: Nama atau Face ID sudah terdaftar.";
        $stmt_check->close();
        $conn->close();
        exit();
    }
    $stmt_check->close();

    // Masukkan data pengguna baru ke tabel `users`
    $stmt_insert = $conn->prepare("INSERT INTO users (nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id) VALUES (?, ?, ?, ?, ?, ?)");
    if ($stmt_insert === false) {
        echo "gagal: Prepare statement insert failed: " . $conn->error;
        $conn->close();
        exit();
    }

    $stmt_insert->bind_param("ssssss", $nama, $alamat, $no_hp, $tanggal_lahir, $jenis_kelamin, $face_id);

    if ($stmt_insert->execute()) {
        $last_id = $conn->insert_id;
        echo "berhasil_daftar_dengan_id:" . $last_id;
    } else {
        echo "gagal: " . $stmt_insert->error;
    }
    $stmt_insert->close();
    
    $conn->close();
} else {
    echo "Metode request tidak valid.";
}
?>
