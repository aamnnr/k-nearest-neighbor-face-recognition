<?php
include 'koneksi.php'; // Pastikan file koneksi.php ada dan berfungsi

// Aktifkan pelaporan error untuk debugging (Hapus di produksi!)
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Set header untuk memastikan respons adalah plain text
header('Content-Type: text/plain');

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    // Ambil data dari POST request, gunakan operator null coalescing (??) untuk menghindari undefined index
    $user_id = $_POST['user_id'] ?? '';
    $nama = $_POST['nama'] ?? '';
    $alamat = $_POST['alamat'] ?? '';
    $no_hp = $_POST['no_hp'] ?? '';
    $tanggal_lahir = $_POST['tanggal_lahir'] ?? '';
    $jenis_kelamin = $_POST['jenis_kelamin'] ?? '';

    // Cek koneksi database
    if ($conn->connect_error) {
        echo "gagal: Error koneksi database: " . $conn->connect_error;
        exit();
    }

    // =====================================================================
    // Validasi Sisi Server di PHP untuk Edit User (Wajib Diisi & Format)
    // =====================================================================
    if (empty($user_id)) {
        echo "gagal: User ID tidak boleh kosong.";
        exit();
    }

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

    // Cek apakah nama yang diubah sudah terdaftar untuk user lain (kecuali user itu sendiri)
    $stmt_check_nama = $conn->prepare("SELECT user_id FROM users WHERE nama = ? AND user_id != ?");
    if ($stmt_check_nama === false) {
        echo "gagal: Prepare statement check nama failed: " . $conn->error;
        $conn->close();
        exit();
    }
    $stmt_check_nama->bind_param("si", $nama, $user_id);
    $stmt_check_nama->execute();
    $stmt_check_nama->store_result();

    if ($stmt_check_nama->num_rows > 0) {
        echo "gagal: Nama '$nama' sudah terdaftar untuk pengguna lain.";
        $stmt_check_nama->close();
        $conn->close();
        exit();
    }
    $stmt_check_nama->close();

    // Perbarui data pengguna di tabel `users`
    $stmt_update = $conn->prepare("UPDATE users SET nama = ?, alamat = ?, no_hp = ?, tanggal_lahir = ?, jenis_kelamin = ? WHERE user_id = ?");
    if ($stmt_update === false) {
        echo "gagal: Prepare statement update failed: " . $conn->error;
        $conn->close();
        exit();
    }

    $stmt_update->bind_param("sssssi", $nama, $alamat, $no_hp, $tanggal_lahir, $jenis_kelamin, $user_id);

    if ($stmt_update->execute()) {
        if ($stmt_update->affected_rows > 0) {
            echo "berhasil";
        } else {
            echo "berhasil: Tidak ada perubahan data atau pengguna tidak ditemukan.";
        }
    } else {
        echo "gagal: " . $stmt_update->error;
    }
    $stmt_update->close();
    $conn->close();
} else {
    echo "Metode request tidak valid.";
}
?>
