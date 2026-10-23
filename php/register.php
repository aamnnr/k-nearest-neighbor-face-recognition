<?php
/** POST nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id -> {user_id}. */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('POST');

$user = validated_user_payload($_POST);
$face_id = input_string($_POST, 'face_id');
if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $face_id)) {
    json_error('Face ID tidak valid.', 422);
}

if (fetch_one('SELECT user_id FROM users WHERE nama = ? OR face_id = ?', 'ss', $user['nama'], $face_id)) {
    json_error('Nama atau Face ID sudah terdaftar.', 409);
}

$stmt = db()->prepare(
    'INSERT INTO users (nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id) VALUES (?, ?, ?, ?, ?, ?)'
);
$stmt->bind_param(
    'ssssss',
    $user['nama'],
    $user['alamat'],
    $user['no_hp'],
    $user['tanggal_lahir'],
    $user['jenis_kelamin'],
    $face_id
);
$stmt->execute();
$user_id = db()->insert_id;
$stmt->close();

json_success(['user_id' => $user_id], 201);
