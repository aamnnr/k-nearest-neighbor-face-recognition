<?php
/**
 * POST user_id, tanggal_absen, waktu_absen, tipe_absen (masuk|pulang), status
 * -> {result: "berhasil" | "sudah" | "belum_masuk"}
 */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('POST');

$user_id = input_positive_int($_POST, 'user_id');
$tanggal = input_string($_POST, 'tanggal_absen');
$waktu = input_string($_POST, 'waktu_absen');
$tipe = input_string($_POST, 'tipe_absen');
$status = mb_substr(input_string($_POST, 'status'), 0, 50);

if ($user_id === null) {
    json_error('User ID tidak valid.', 422);
}
if (!is_valid_date($tanggal) || !is_valid_time($waktu)) {
    json_error('Format tanggal/waktu absen tidak valid.', 422);
}
if (!in_array($tipe, ['masuk', 'pulang'], true)) {
    json_error('Tipe absen tidak valid.', 422);
}

$record = fetch_one(
    'SELECT waktu_masuk, waktu_pulang FROM absensi WHERE user_id = ? AND tanggal = ?',
    'is',
    $user_id,
    $tanggal
);

if ($tipe === 'masuk') {
    if ($record !== null) {
        json_success(['result' => 'sudah']);
    }
    $stmt = db()->prepare(
        'INSERT INTO absensi (user_id, tanggal, waktu_masuk, status_masuk) VALUES (?, ?, ?, ?)'
    );
    $stmt->bind_param('isss', $user_id, $tanggal, $waktu, $status);
    try {
        $stmt->execute();
    } catch (mysqli_sql_exception $e) {
        // 1062 = duplicate entry (UNIQUE user_id + tanggal): request bersamaan
        if ($e->getCode() === 1062) {
            json_success(['result' => 'sudah']);
        }
        throw $e;
    }
    $stmt->close();
    json_success(['result' => 'berhasil']);
}

// tipe === 'pulang'
if ($record === null || $record['waktu_masuk'] === null) {
    json_success(['result' => 'belum_masuk']);
}
if ($record['waktu_pulang'] !== null) {
    json_success(['result' => 'sudah']);
}

$stmt = db()->prepare(
    'UPDATE absensi SET waktu_pulang = ?, status_pulang = ? WHERE user_id = ? AND tanggal = ? AND waktu_pulang IS NULL'
);
$stmt->bind_param('ssis', $waktu, $status, $user_id, $tanggal);
$stmt->execute();
$updated = $stmt->affected_rows;
$stmt->close();

json_success(['result' => $updated > 0 ? 'berhasil' : 'sudah']);
