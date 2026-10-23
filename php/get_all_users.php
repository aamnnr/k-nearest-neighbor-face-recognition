<?php
/** GET -> daftar semua pengguna. */

declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

api_init('GET');

$result = db()->query(
    'SELECT user_id, nama, alamat, no_hp, tanggal_lahir, jenis_kelamin, face_id FROM users ORDER BY nama ASC'
);

json_success($result->fetch_all(MYSQLI_ASSOC));
