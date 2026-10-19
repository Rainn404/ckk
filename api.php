<?php
/**
 * SIPEKA DF - PHP API Proxy (api.php)
 * Meneruskan semua request API dari Apache/XAMPP ke Python backend (port 8080).
 * PHP hanya bertugas sebagai proxy - SEMUA logika ada di Python.
 *
 * Cara kerja:
 *   Browser → Apache → api.php → Python:8080/api/... → api.php → Browser
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight OPTIONS
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Python backend URL
define('PYTHON_API_BASE', 'http://127.0.0.1:8080/api');

// Ambil endpoint dari URL path atau query string
// Mendukung: /sipeka/api.php?endpoint=/history  ATAU  /sipeka/api/history (via .htaccess)
$endpoint = '';
if (isset($_GET['endpoint'])) {
    $endpoint = '/' . ltrim($_GET['endpoint'], '/');
} elseif (isset($_SERVER['PATH_INFO'])) {
    $endpoint = $_SERVER['PATH_INFO'];
}

// Keamanan: Hanya izinkan endpoint yang diketahui
$allowed_endpoints = [
    '/history',
    '/history/delete',
    '/upload-and-compare',
    '/export/csv',
    '/export/print',
    '/export/html',
    '/history/'
];

$is_allowed = false;
foreach ($allowed_endpoints as $allowed) {
    if (strpos($endpoint, $allowed) === 0) {
        $is_allowed = true;
        break;
    }
}

if (!$is_allowed) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Endpoint tidak dikenali: ' . $endpoint]);
    exit();
}

$python_url = PYTHON_API_BASE . $endpoint;

// Inisialisasi cURL
$ch = curl_init();

// Method & Body
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'POST') {
    $content_type = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';
    
    if (strpos($content_type, 'multipart/form-data') !== false) {
        // File upload - teruskan sebagai multipart
        $post_data = [];
        if (!empty($_FILES)) {
            foreach ($_FILES as $key => $file) {
                if ($file['error'] === UPLOAD_ERR_OK) {
                    $post_data[$key] = new CURLFile($file['tmp_name'], $file['type'], $file['name']);
                }
            }
        }
        foreach ($_POST as $key => $value) {
            $post_data[$key] = $value;
        }
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post_data);
    } else {
        // JSON body
        $raw_body = file_get_contents('php://input');
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $raw_body);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    }
} elseif ($method === 'DELETE') {
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
    $raw_body = file_get_contents('php://input');
    if ($raw_body) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $raw_body);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    }
}

// Build full URL with query params jika ada
$query = '';
$skip_keys = ['endpoint'];
$params = [];
foreach ($_GET as $k => $v) {
    if (!in_array($k, $skip_keys)) {
        $params[$k] = $v;
    }
}
if (!empty($params)) {
    $query = '?' . http_build_query($params);
}

curl_setopt($ch, CURLOPT_URL, $python_url . $query);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 60); // Timeout 60 detik untuk upload PDF besar
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);

$response     = curl_exec($ch);
$http_code    = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curl_error   = curl_error($ch);
$content_type = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
curl_close($ch);

if ($curl_error) {
    http_response_code(503);
    echo json_encode([
        'success' => false,
        'error'   => 'Server Python tidak dapat dijangkau. Pastikan run.bat sudah dijalankan.',
        'detail'  => $curl_error
    ]);
    exit();
}

// Teruskan Content-Type dari Python (bisa jadi text/csv untuk ekspor)
if ($content_type) {
    header('Content-Type: ' . $content_type);
}

// Teruskan Content-Disposition jika ada (untuk download)
http_response_code($http_code);
echo $response;
