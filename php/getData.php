<?php
/** GET [?tanggal=YYYY-MM-DD] [&user_id=<int>] -> daftar catatan presensi. */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('GET');

$sql = 'SELECT a.absen_id, u.nama, a.tanggal, a.waktu_masuk, a.status_masuk, a.waktu_pulang, a.status_pulang
        FROM absensi a
        JOIN users u ON a.user_id = u.user_id';

$conditions = [];
$params = [];
$types = '';

if (!empty($_GET['user_id'])) {
    $user_id = input_positive_int($_GET, 'user_id');
    if ($user_id === null) {
        json_error('User ID tidak valid.', 422);
    }
    $conditions[] = 'a.user_id = ?';
    $params[] = $user_id;
    $types .= 'i';
}

if (!empty($_GET['tanggal'])) {
    $tanggal = input_string($_GET, 'tanggal');
    if (!is_valid_date($tanggal)) {
        json_error('Format tanggal tidak valid (YYYY-MM-DD).', 422);
    }
    $conditions[] = 'a.tanggal = ?';
    $params[] = $tanggal;
    $types .= 's';
}

if ($conditions) {
    $sql .= ' WHERE ' . implode(' AND ', $conditions);
}
$sql .= ' ORDER BY a.tanggal DESC, u.nama ASC';

$stmt = db()->prepare($sql);
if ($params) {
    $stmt->bind_param($types, ...$params);
}
$stmt->execute();
$rows = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
$stmt->close();

json_success($rows);
