<?php
include 'koneksi.php';

error_reporting(E_ALL);
ini_set('display_errors', 1);

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $user_id = $_POST['user_id'];

    if ($conn->connect_error) {
        echo "error_koneksi: " . $conn->connect_error;
        exit();
    }

    // Hapus pengguna dari tabel 'users'
    $stmt = $conn->prepare("DELETE FROM users WHERE user_id = ?");
    $stmt->bind_param("i", $user_id);

    if ($stmt->execute()) {
        echo "berhasil";
    } else {
        echo "gagal: " . $conn->error;
    }
    $stmt->close();
    $conn->close();
} else {
    echo "Metode request tidak valid.";
}
?>