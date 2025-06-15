<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);

// Konfigurasi Database
$servername = "localhost"; 
$username = "root";        
$password = "";            
$dbname = "presensi_wajah";          

// Membuat koneksi database
$conn = new mysqli($servername, $username, $password, $dbname);

// Memeriksa koneksi
if ($conn->connect_error) {
    die("Koneksi database GAGAL: " . $conn->connect_error);
}

$conn->set_charset("utf8mb4");
?>