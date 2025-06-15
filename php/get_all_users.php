<?php
include 'koneksi.php';

error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: application/json');

$response = [];

if ($conn->connect_error) {
    $response = ["error" => "Koneksi database gagal: " . $conn->connect_error];
    echo json_encode($response);
    exit();
}

$sql = "SELECT user_id, nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id FROM users ORDER BY nama ASC";
$result = $conn->query($sql);

if ($result) {
    if ($result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            $response[] = $row;
        }
    } else {
        $response = [];
    }
} else {
    error_log("Database query failed in get_all_users.php: " . $conn->error);
    $response = ["error" => "Failed to retrieve users due to query error."];
}

$conn->close();
echo json_encode($response);
?>