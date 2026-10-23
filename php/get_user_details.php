<?php
/** GET ?user_id=<int> atau ?face_id=<uuid> -> detail satu pengguna. */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('GET');

$columns = 'user_id, nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id';

if (isset($_GET['user_id'])) {
    $user_id = input_positive_int($_GET, 'user_id');
    if ($user_id === null) {
        json_error('User ID tidak valid.', 422);
    }
    $user = fetch_one("SELECT $columns FROM users WHERE user_id = ?", 'i', $user_id);
} elseif (isset($_GET['face_id'])) {
    $face_id = input_string($_GET, 'face_id');
    $user = fetch_one("SELECT $columns FROM users WHERE face_id = ?", 's', $face_id);
} else {
    json_error('User ID atau Face ID wajib diisi.', 422);
}

if ($user === null) {
    json_error('Pengguna tidak ditemukan.', 404);
}

json_success($user);
