<?php
include 'koneksi.php';

error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: application/json');

$response = [];

if (isset($_GET['user_id'])) {
    $param_type = "i";
    $param_value = $_GET['user_id'];
    $where_clause = "user_id = ?";
} elseif (isset($_GET['face_id'])) { // Tambahkan pengecekan face_id
    $param_type = "s";
    $param_value = $_GET['face_id'];
    $where_clause = "face_id = ?";
} else {
    $response = ["error" => "User ID or Face ID not provided."];
    echo json_encode($response);
    exit();
}

if ($conn->connect_error) {
    $response = ["error" => "Koneksi database gagal: " . $conn->connect_error];
    echo json_encode($response);
    exit();
}

// Sesuaikan query berdasarkan parameter yang diterima
$stmt = $conn->prepare("SELECT user_id, nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id FROM users WHERE " . $where_clause);
$stmt->bind_param($param_type, $param_value);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows > 0) {
    $row = $result->fetch_assoc();
    $response = $row;
} else {
    $response = ["error" => "User not found."];
}
$stmt->close();
$conn->close();

echo json_encode($response);
?>