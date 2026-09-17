<?php
declare(strict_types=1);

const WTHO_ROOT = __DIR__ . '/../..';
const WTHO_DATA = WTHO_ROOT . '/data';
const WTHO_WORKS = WTHO_ROOT . '/works';
const WTHO_BACKUPS = WTHO_DATA . '/backups';
const WTHO_CONFIG = __DIR__ . '/../config.php';

session_start([
  'cookie_httponly' => true,
  'cookie_samesite' => 'Lax',
  'cookie_secure' => (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off'),
]);

function wtho_config(): ?array {
  if (!is_file(WTHO_CONFIG)) return null;
  $cfg = include WTHO_CONFIG;
  return is_array($cfg) ? $cfg : null;
}

function wtho_needs_setup(): bool {
  $cfg = wtho_config();
  return !$cfg || empty($cfg['password_hash']);
}

function wtho_logged_in(): bool {
  return !empty($_SESSION['wtho_admin']);
}

function wtho_require_login(): void {
  if (wtho_needs_setup()) {
    header('Location: setup.php');
    exit;
  }
  if (!wtho_logged_in()) {
    header('Location: login.php');
    exit;
  }
}

function wtho_csrf_token(): string {
  if (empty($_SESSION['csrf'])) {
    $_SESSION['csrf'] = bin2hex(random_bytes(16));
  }
  return $_SESSION['csrf'];
}

function wtho_csrf_check(): void {
  $ok = isset($_POST['csrf'], $_SESSION['csrf'])
    && hash_equals($_SESSION['csrf'], (string)$_POST['csrf']);
  if (!$ok) {
    http_response_code(400);
    exit('Ungültige Sitzung. Bitte zurück und erneut speichern.');
  }
}

function wtho_h(?string $s): string {
  return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function wtho_flash(?string $msg = null): ?string {
  if ($msg !== null) {
    $_SESSION['flash'] = $msg;
    return null;
  }
  $out = $_SESSION['flash'] ?? null;
  unset($_SESSION['flash']);
  return $out;
}

function wtho_read_json(string $file): mixed {
  $path = WTHO_DATA . '/' . $file;
  $raw = @file_get_contents($path);
  if ($raw === false) {
    throw new RuntimeException("Datei fehlt: $file");
  }
  $data = json_decode($raw, true);
  if (!is_array($data)) {
    throw new RuntimeException("JSON ungültig: $file");
  }
  return $data;
}

function wtho_write_json(string $file, mixed $data): void {
  if (!is_dir(WTHO_BACKUPS)) {
    mkdir(WTHO_BACKUPS, 0755, true);
  }
  $path = WTHO_DATA . '/' . $file;
  if (is_file($path)) {
    $stamp = date('Ymd-His');
    copy($path, WTHO_BACKUPS . '/' . basename($file, '.json') . "-$stamp.json");
    $old = glob(WTHO_BACKUPS . '/' . basename($file, '.json') . '-*.json') ?: [];
    rsort($old);
    foreach (array_slice($old, 20) as $extra) {
      @unlink($extra);
    }
  }
  $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
  if ($json === false) {
    throw new RuntimeException('JSON konnte nicht geschrieben werden.');
  }
  $tmp = $path . '.tmp';
  if (file_put_contents($tmp, $json . "\n", LOCK_EX) === false) {
    throw new RuntimeException("Keine Schreibrechte für $file");
  }
  rename($tmp, $path);
}

function wtho_slug(string $s): string {
  $map = ['ä'=>'ae','ö'=>'oe','ü'=>'ue','Ä'=>'ae','Ö'=>'oe','Ü'=>'ue','ß'=>'ss'];
  $s = strtr($s, $map);
  $s = strtolower($s);
  $s = preg_replace('/[^a-z0-9]+/', '-', $s) ?? '';
  return trim($s, '-') ?: 'work';
}

function wtho_find_work(array $works, string $id): ?int {
  foreach ($works as $i => $w) {
    if (($w['id'] ?? '') === $id) return $i;
  }
  return null;
}

function wtho_set_hero(array &$site, array &$works, string $id): void {
  $site['heroWorkId'] = $id;
  foreach ($works as &$w) {
    $w['hero'] = (($w['id'] ?? '') === $id);
  }
  unset($w);
}

function wtho_ensure_work_page(string $id, array $work): void {
  $dir = WTHO_WORKS . '/' . $id;
  if (!is_dir($dir)) mkdir($dir, 0755, true);
  $page = $dir . '/index.html';
  $title = $work['title']['en'] ?? $work['title']['de'] ?? $id;
  $year = $work['year'] ?? '';
  $medium = $work['medium']['de'] ?? '';
  $size = $work['size'] ?? '';
  $meta = trim($medium . ($size && $size !== '—' ? ' · ' . $size : ''));
  $cover = ($work['images'][0] ?? $id . '.jpg');
  $statement = $work['statement']['de'] ?? '';
  $html = <<<HTML
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{$title} — wtho.art</title>
  <meta name="description" content="{$title} — {$meta}. Thorsten Weitz, wtho.art." />
  <link rel="canonical" href="https://wtho.art/works/{$id}/" />
  <link rel="icon" type="image/svg+xml" href="../../favicon.svg" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{$title} — wtho.art" />
  <meta property="og:description" content="{$meta}" />
  <meta property="og:image" content="https://wtho.art/works/{$id}/{$cover}" />
  <meta property="og:url" content="https://wtho.art/works/{$id}/" />
  <link rel="stylesheet" href="/works/work.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet" />
</head>
<body>
  <p class="fallback">Diese Seite lädt Texte aus data/works.json. Falls Sie das sehen, fehlt die Vorlage — öffnen Sie ein bestehendes Werk und kopieren Sie dessen index.html.</p>
  <script src="../../js/content.js"></script>
  <script src="../../js/work-page.js"></script>
</body>
</html>
HTML;
  // Prefer cloning a real styled page if one exists.
  $donor = null;
  foreach (glob(WTHO_WORKS . '/*/index.html') ?: [] as $candidate) {
    if (basename(dirname($candidate)) === $id) continue;
    $donor = $candidate;
    break;
  }
  if ($donor && is_file($donor)) {
    $src = file_get_contents($donor);
    if ($src !== false) {
      file_put_contents($page, $src);
      return;
    }
  }
  file_put_contents($page, $html);
}

function wtho_save_upload(string $id, array $file): ?string {
  if (($file['error'] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) return null;
  if (($file['error'] ?? 0) !== UPLOAD_ERR_OK) {
    throw new RuntimeException('Upload fehlgeschlagen (Code ' . $file['error'] . ').');
  }
  if (($file['size'] ?? 0) > 8 * 1024 * 1024) {
    throw new RuntimeException('Bild größer als 8 MB. Bitte fürs Web verkleinern.');
  }
  $finfo = new finfo(FILEINFO_MIME_TYPE);
  $mime = $finfo->file($file['tmp_name']);
  $exts = [
    'image/jpeg' => 'jpg',
    'image/png' => 'png',
    'image/webp' => 'webp',
  ];
  if (!isset($exts[$mime])) {
    throw new RuntimeException('Nur JPG, PNG oder WebP.');
  }
  $base = wtho_slug(pathinfo($file['name'], PATHINFO_FILENAME));
  if ($base === 'work') $base = $id;
  $name = $base . '.' . $exts[$mime];
  $dir = WTHO_WORKS . '/' . $id;
  if (!is_dir($dir)) mkdir($dir, 0755, true);
  $dest = $dir . '/' . $name;
  $n = 2;
  while (is_file($dest)) {
    $name = $base . '-' . $n . '.' . $exts[$mime];
    $dest = $dir . '/' . $name;
    $n++;
  }
  if (!move_uploaded_file($file['tmp_name'], $dest)) {
    throw new RuntimeException('Datei konnte nicht gespeichert werden.');
  }
  return $name;
}
