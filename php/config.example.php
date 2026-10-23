<?php
/**
 * Contoh konfigurasi. Salin file ini menjadi `config.local.php` lalu isi nilainya.
 * `config.local.php` sudah masuk .gitignore sehingga tidak ikut ter-commit.
 *
 * Alternatif: atur environment variable DB_HOST, DB_USER, DB_PASS, DB_NAME, PHP_API_KEY.
 */
return [
    'db_host' => 'localhost',
    'db_user' => 'root',
    'db_pass' => '',
    'db_name' => 'presensi_wajah',
    // Harus sama dengan PHP_API_KEY di file .env aplikasi Python.
    // Buat nilai acak, mis.: python -c "import secrets; print(secrets.token_hex(32))"
    'api_key' => '',
];
