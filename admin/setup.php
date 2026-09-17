<?php
declare(strict_types=1);
require __DIR__ . '/inc/bootstrap.php';

if (!wtho_needs_setup()) {
  header('Location: login.php');
  exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $a = (string)($_POST['password'] ?? '');
  $b = (string)($_POST['password2'] ?? '');
  if (strlen($a) < 10) {
    $error = 'Mindestens 10 Zeichen.';
  } elseif ($a !== $b) {
    $error = 'Passwörter stimmen nicht überein.';
  } else {
    $php = "<?php\nreturn [\n  'password_hash' => " . var_export(password_hash($a, PASSWORD_DEFAULT), true) . ",\n];\n";
    if (file_put_contents(WTHO_CONFIG, $php, LOCK_EX) === false) {
      $error = 'config.php konnte nicht geschrieben werden. Ordner admin/ muss beschreibbar sein.';
    } else {
      header('Location: login.php?setup=1');
      exit;
    }
  }
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Admin einrichten — wtho.art</title>
  <link rel="stylesheet" href="assets/admin.css" />
</head>
<body>
  <div class="auth">
    <h1>Admin einrichten</h1>
    <p class="muted">Einmalig ein Passwort setzen. Es wird nur auf dem Server gespeichert, nicht auf GitHub.</p>
    <?php if ($error): ?><p class="error"><?= wtho_h($error) ?></p><?php endif; ?>
    <form method="post">
      <label>Passwort</label>
      <input type="password" name="password" required minlength="10" autocomplete="new-password" />
      <label>Passwort wiederholen</label>
      <input type="password" name="password2" required minlength="10" autocomplete="new-password" />
      <p class="actions"><button class="btn" type="submit">Speichern</button></p>
    </form>
  </div>
</body>
</html>
