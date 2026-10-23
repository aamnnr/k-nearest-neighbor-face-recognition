<?php
/** POST user_id -> hapus pengguna (catatan presensi ikut terhapus lewat ON DELETE CASCADE). */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('POST');

$user_id = input_positive_int($_POST, 'user_id');
if ($user_id === null) {
    json_error('User ID tidak valid.', 422);
}

$stmt = db()->prepare('DELETE FROM users WHERE user_id = ?');
$stmt->bind_param('i', $user_id);
$stmt->execute();
$deleted = $stmt->affected_rows;
$stmt->close();

if ($deleted === 0) {
    json_error('Pengguna tidak ditemukan.', 404);
}

json_success(['user_id' => $user_id]);
