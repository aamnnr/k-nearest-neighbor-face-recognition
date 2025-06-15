<?php
include 'koneksi.php';

error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: application/json');

$response = [];

if (isset($_GET['user_id'])) {
    $user_id = $_GET['user_id'];

    if ($conn->connect_error) {
        $response = ["error" => "Koneksi database gagal: " . $conn->connect_error];
        echo json_encode($response);
        exit();
    }

    $stmt = $conn->prepare("SELECT user_id, nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id FROM users WHERE user_id = ?");
    $stmt->bind_param("i", $user_id);
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
} else {
    $response = ["error" => "User ID not provided."];
}

echo json_encode($response);
?>