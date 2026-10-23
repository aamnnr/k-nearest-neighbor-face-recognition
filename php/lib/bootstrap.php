<?php
/**
 * Bootstrap bersama untuk semua endpoint API: konfigurasi, koneksi database,
 * autentikasi API key, respons JSON, dan validasi input.
 */

declare(strict_types=1);

ini_set('display_errors', '0');
ini_set('log_errors', '1');
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

set_exception_handler(function (Throwable $e): void {
    error_log('[presensi_wajah] ' . $e);
    json_error('Terjadi kesalahan pada server.', 500);
});

const GENDER_OPTIONS = ['Laki-laki', 'Perempuan'];

function app_config(): array
{
    static $config = null;
    if ($config !== null) {
        return $config;
    }

    $local = __DIR__ . '/../config.local.php';
    $file = is_file($local) ? require $local : [];
    $env = static fn (string $name, string $default = ''): string => getenv($name) !== false ? (string) getenv($name) : $default;

    $config = [
        'db_host' => $file['db_host'] ?? $env('DB_HOST', 'localhost'),
        'db_user' => $file['db_user'] ?? $env('DB_USER', 'root'),
        'db_pass' => $file['db_pass'] ?? $env('DB_PASS'),
        'db_name' => $file['db_name'] ?? $env('DB_NAME', 'presensi_wajah'),
        'api_key' => $file['api_key'] ?? $env('PHP_API_KEY'),
    ];
    return $config;
}

function json_response(int $status, array $payload): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function json_success($data = null, int $status = 200): void
{
    json_response($status, ['status' => 'success', 'data' => $data]);
}

function json_error(string $message, int $status = 400): void
{
    json_response($status, ['status' => 'error', 'message' => $message]);
}

function require_method(string $method): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== $method) {
        header('Allow: ' . $method);
        json_error('Metode request tidak valid.', 405);
    }
}

function require_api_key(): void
{
    $expected = app_config()['api_key'];
    if ($expected === '') {
        json_error('API key server belum dikonfigurasi (lihat php/config.example.php).', 500);
    }
    $given = $_SERVER['HTTP_X_API_KEY'] ?? '';
    if (!is_string($given) || !hash_equals($expected, $given)) {
        json_error('Tidak diizinkan.', 401);
    }
}

function db(): mysqli
{
    static $conn = null;
    if ($conn === null) {
        mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
        $cfg = app_config();
        $conn = new mysqli($cfg['db_host'], $cfg['db_user'], $cfg['db_pass'], $cfg['db_name']);
        $conn->set_charset('utf8mb4');
    }
    return $conn;
}

/** Inisialisasi standar endpoint: cek metode lalu API key. */
function api_init(string $method): void
{
    require_method($method);
    require_api_key();
}

function input_string(array $source, string $key): string
{
    $value = $source[$key] ?? '';
    return is_string($value) ? trim($value) : '';
}

function input_positive_int(array $source, string $key): ?int
{
    $value = filter_var($source[$key] ?? null, FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
    return $value === false ? null : $value;
}

function is_valid_date(string $value): bool
{
    $date = DateTimeImmutable::createFromFormat('!Y-m-d', $value);
    return $date !== false && $date->format('Y-m-d') === $value;
}

function is_valid_time(string $value): bool
{
    $time = DateTimeImmutable::createFromFormat('!H:i:s', $value);
    return $time !== false && $time->format('H:i:s') === $value;
}

/**
 * Validasi data diri pengguna dari POST. Mengembalikan array data bersih;
 * menghentikan request dengan error 422 bila tidak valid.
 */
function validated_user_payload(array $source): array
{
    $data = [
        'nama' => preg_replace('/\s+/u', ' ', input_string($source, 'nama')),
        'alamat' => input_string($source, 'alamat'),
        'no_hp' => input_string($source, 'no_hp'),
        'tanggal_lahir' => input_string($source, 'tanggal_lahir'),
        'jenis_kelamin' => input_string($source, 'jenis_kelamin'),
    ];

    if ($data['nama'] === '' || mb_strlen($data['nama']) > 100 || !preg_match('/^[\p{L}\s]+$/u', $data['nama'])) {
        json_error('Nama wajib diisi, maksimal 100 karakter, dan hanya berisi huruf serta spasi.', 422);
    }
    if ($data['alamat'] === '' || mb_strlen($data['alamat']) > 255) {
        json_error('Alamat wajib diisi dan maksimal 255 karakter.', 422);
    }
    if (!preg_match('/^[0-9]{10,15}$/', $data['no_hp'])) {
        json_error('Format nomor HP tidak valid (10-15 digit angka).', 422);
    }
    if (!is_valid_date($data['tanggal_lahir']) || $data['tanggal_lahir'] > date('Y-m-d')) {
        json_error('Tanggal lahir tidak valid atau berada di masa depan.', 422);
    }
    if (!in_array($data['jenis_kelamin'], GENDER_OPTIONS, true)) {
        json_error('Pilihan jenis kelamin tidak valid.', 422);
    }
    return $data;
}

/** Ambil satu baris hasil prepared statement sebagai array asosiatif (atau null). */
function fetch_one(string $sql, string $types, ...$params): ?array
{
    $stmt = db()->prepare($sql);
    $stmt->bind_param($types, ...$params);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    return $row ?: null;
}
