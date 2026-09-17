<?php
declare(strict_types=1);
require __DIR__ . '/inc/bootstrap.php';

if (wtho_needs_setup()) {
  header('Location: setup.php');
  exit;
}
if (wtho_logged_in()) {
  header('Location: index.php');
  exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $cfg = wtho_config();
  $pw = (string)($_POST['password'] ?? '');
  if ($cfg && password_verify($pw, (string)$cfg['password_hash'])) {
    $_SESSION['wtho_admin'] = true;
    session_regenerate_id(true);
    header('Location: index.php');
    exit;
  }
  $error = 'Falsches Passwort.';
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Anmelden — wtho.art Admin</title>
  <link rel="stylesheet" href="assets/admin.css" />
</head>
<body>
  <div class="auth">
    <h1>wtho.art Admin</h1>
    <?php if (!empty($_GET['setup'])): ?><p class="flash">Passwort gesetzt. Jetzt anmelden.</p><?php endif; ?>
    <?php if ($error): ?><p class="error"><?= wtho_h($error) ?></p><?php endif; ?>
    <form method="post">
      <label>Passwort</label>
      <input type="password" name="password" required autocomplete="current-password" />
      <p class="actions"><button class="btn" type="submit">Anmelden</button></p>
    </form>
  </div>
</body>
</html>
