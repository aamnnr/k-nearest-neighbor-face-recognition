<?php
/** POST user_id, nama, alamat, no_hp, tanggal_lahir, jenis_kelamin -> perbarui data pengguna. */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('POST');

$user_id = input_positive_int($_POST, 'user_id');
if ($user_id === null) {
    json_error('User ID tidak valid.', 422);
}
$user = validated_user_payload($_POST);

if (!fetch_one('SELECT user_id FROM users WHERE user_id = ?', 'i', $user_id)) {
    json_error('Pengguna tidak ditemukan.', 404);
}
if (fetch_one('SELECT user_id FROM users WHERE nama = ? AND user_id != ?', 'si', $user['nama'], $user_id)) {
    json_error("Nama '{$user['nama']}' sudah terdaftar untuk pengguna lain.", 409);
}

$stmt = db()->prepare(
    'UPDATE users SET nama = ?, alamat = ?, no_hp = ?, tanggal_lahir = ?, jenis_kelamin = ? WHERE user_id = ?'
);
$stmt->bind_param(
    'sssssi',
    $user['nama'],
    $user['alamat'],
    $user['no_hp'],
    $user['tanggal_lahir'],
    $user['jenis_kelamin'],
    $user_id
);
$stmt->execute();
$stmt->close();

json_success(['user_id' => $user_id]);
