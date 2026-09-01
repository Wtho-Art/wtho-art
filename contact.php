<?php
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['ok' => false, 'error' => 'method']);
  exit;
}

$name = trim((string) ($_POST['name'] ?? ''));
$email = trim((string) ($_POST['email'] ?? ''));
$work = trim((string) ($_POST['work'] ?? ''));
$message = trim((string) ($_POST['message'] ?? ''));

$email = str_replace(["\r", "\n"], '', $email);
$name = str_replace(["\r", "\n"], '', $name);
$work = str_replace(["\r", "\n"], '', $work);

if ($name === '' || $message === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
  http_response_code(400);
  echo json_encode(['ok' => false, 'error' => 'invalid']);
  exit;
}

$to = 'Wtho.Art@proton.me';
$subject = 'Anfrage wtho.art' . ($work !== '' ? ': ' . $work : '');
$body = "Name: {$name}\nE-Mail: {$email}\nWerk: " . ($work !== '' ? $work : '—') . "\n\n{$message}\n";
$headers = [
  'From: wtho.art <' . $to . '>',
  'Reply-To: ' . $email,
  'Content-Type: text/plain; charset=UTF-8',
  'X-Mailer: wtho.art',
];

$ok = @mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, implode("\r\n", $headers));
echo json_encode(['ok' => (bool) $ok]);
