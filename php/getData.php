<?php
include 'koneksi.php'; // Pastikan file koneksi.php ada dan berfungsi

error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: application/json');

$response = [];

if ($conn->connect_error) {
    $response = ["error" => "Koneksi database gagal: " . $conn->connect_error];
    echo json_encode($response);
    exit();
}

$sql = "SELECT
            a.absen_id,
            u.nama,
            a.tanggal,
            a.waktu_masuk,
            a.status_masuk,
            a.waktu_pulang,
            a.status_pulang
        FROM
            absensi a
        JOIN
            users u ON a.user_id = u.user_id";

$conditions = []; // Array untuk menyimpan kondisi WHERE
$params = [];    // Array untuk menyimpan parameter bind_param
$types = "";     // String untuk menyimpan tipe parameter bind_param

// Tambahkan kondisi untuk user_id jika ada di parameter GET
if (isset($_GET['user_id']) && !empty($_GET['user_id'])) {
    $user_id_filter = $_GET['user_id'];
    $conditions[] = "a.user_id = ?"; // Tambahkan kondisi user_id
    $params[] = $user_id_filter;
    $types .= "i"; // 'i' untuk integer (user_id adalah INT)
}

// Tambahkan kondisi untuk tanggal jika ada di parameter GET
if (isset($_GET['tanggal']) && !empty($_GET['tanggal'])) {
    $tanggal_filter = $_GET['tanggal'];
    $conditions[] = "a.tanggal = ?"; // Tambahkan kondisi tanggal
    $params[] = $tanggal_filter;
    $types .= "s"; // 's' untuk string (tanggal adalah DATE/VARCHAR)
}

// Gabungkan semua kondisi ke dalam query SQL menggunakan WHERE dan AND
if (!empty($conditions)) {
    $sql .= " WHERE " . implode(" AND ", $conditions);
}

$sql .= " ORDER BY a.tanggal DESC, u.nama ASC"; // Urutkan hasil untuk konsistensi

$stmt = $conn->prepare($sql);

if ($stmt === false) {
    error_log("Prepare statement failed in getData.php: " . $conn->error);
    $response = ["error" => "Failed to prepare query."];
    echo json_encode($response);
    $conn->close();
    exit();
}

// Bind parameter hanya jika ada kondisi yang ditambahkan
if (!empty($params)) {
    // ...$params digunakan untuk unpack array params ke argumen individual
    $stmt->bind_param($types, ...$params);
}

$stmt->execute();
$result = $stmt->get_result();

if ($result) {
    if ($result->num_rows > 0) {
        // Karena kita sekarang memfilter per user_id dan tanggal,
        // seharusnya hanya ada maksimal 1 baris per user per hari.
        // Jika dipanggil tanpa user_id, ini akan mengembalikan semua data yang cocok dengan tanggal.
        while($row = $result->fetch_assoc()) {
            $response[] = $row;
        }
    } else {
        $response = []; // Jika tidak ada data yang cocok
    }
} else {
    error_log("Database query failed in getData.php: " . $stmt->error);
    $response = ["error" => "Failed to retrieve attendance data due to query error."];
}

$stmt->close();
$conn->close();
echo json_encode($response);
?>
