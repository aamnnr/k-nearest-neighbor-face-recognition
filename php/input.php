<?php
include 'koneksi.php';

// Aktifkan pelaporan error untuk debugging (Hapus di produksi!)
error_reporting(E_ALL);
ini_set('display_errors', 1);

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $user_id = $_POST['user_id'];
    $tanggal_absen = $_POST['tanggal_absen']; 
    $waktu_absen = $_POST['waktu_absen'];    
    $tipe_absen = $_POST['tipe_absen'];
    $status = $_POST['status'];

    $response = "gagal";

    if ($conn->connect_error) {
        $response = "error_koneksi: " . $conn->connect_error;
        echo $response;
        exit();
    }

    if ($tipe_absen == 'masuk') {
        // Cek apakah sudah absen masuk hari ini untuk user_id dan tanggal ini
        $stmt_check = $conn->prepare("SELECT COUNT(*) FROM absensi WHERE user_id = ? AND tanggal = ?");
        $stmt_check->bind_param("is", $user_id, $tanggal_absen);
        $stmt_check->execute();
        $stmt_check->bind_result($count);
        $stmt_check->fetch();
        $stmt_check->close();

        if ($count > 0) {
            $response = "sudah"; // Sudah ada entri absen masuk untuk hari ini
        } else {
            // Lakukan INSERT untuk absen masuk
            $stmt_insert = $conn->prepare("INSERT INTO absensi (user_id, tanggal, waktu_masuk, status_masuk) VALUES (?, ?, ?, ?)");
            $stmt_insert->bind_param("isss", $user_id, $tanggal_absen, $waktu_absen, $status);
            if ($stmt_insert->execute()) {
                $response = "berhasil";
            } else {
                // Tangani error INSERT (misal, duplicate entry jika UNIQUE KEY diaktifkan tapi logic cek gagal)
                $response = "gagal_insert_masuk: " . $conn->error;
            }
            $stmt_insert->close();
        }
    } elseif ($tipe_absen == 'pulang') {
        // Cek apakah sudah ada entri absen masuk untuk hari ini dan user_id ini
        $stmt_check_masuk = $conn->prepare("SELECT COUNT(*) FROM absensi WHERE user_id = ? AND tanggal = ? AND waktu_masuk IS NOT NULL");
        $stmt_check_masuk->bind_param("is", $user_id, $tanggal_absen);
        $stmt_check_masuk->execute();
        $stmt_check_masuk->bind_result($count_masuk);
        $stmt_check_masuk->fetch();
        $stmt_check_masuk->close();

        if ($count_masuk == 0) {
            $response = "belum_masuk"; // Belum absen masuk, tidak bisa absen pulang
        } else {
            // Cek apakah sudah absen pulang hari ini
            $stmt_check_pulang = $conn->prepare("SELECT COUNT(*) FROM absensi WHERE user_id = ? AND tanggal = ? AND waktu_pulang IS NOT NULL");
            $stmt_check_pulang->bind_param("is", $user_id, $tanggal_absen);
            $stmt_check_pulang->execute();
            $stmt_check_pulang->bind_result($count_pulang);
            $stmt_check_pulang->fetch();
            $stmt_check_pulang->close();

            if ($count_pulang > 0) {
                $response = "sudah"; // Sudah absen pulang
            } else {
                // Lakukan UPDATE untuk absen pulang pada baris yang sama
                $stmt_update = $conn->prepare("UPDATE absensi SET waktu_pulang = ?, status_pulang = ? WHERE user_id = ? AND tanggal = ?");
                $stmt_update->bind_param("ssis", $waktu_absen, $status, $user_id, $tanggal_absen);
                if ($stmt_update->execute()) {
                    $response = "berhasil";
                } else {
                    $response = "gagal_update_pulang: " . $conn->error;
                }
                $stmt_update->close();
            }
        }
    }
    echo $response;
    $conn->close();
} else {
    echo "Metode request tidak valid.";
}
?>