<?php
declare(strict_types=1);
require __DIR__ . '/inc/bootstrap.php';
require __DIR__ . '/inc/layout.php';
wtho_require_login();

$works = wtho_read_json('works.json');
$site = wtho_read_json('site.json');
$hero = (string)($site['heroWorkId'] ?? '');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  wtho_csrf_check();
  $action = (string)($_POST['action'] ?? '');
  $id = (string)($_POST['id'] ?? '');
  $idx = $id !== '' ? wtho_find_work($works, $id) : null;

  if ($action === 'hero' && $idx !== null) {
    wtho_set_hero($site, $works, $id);
    wtho_write_json('works.json', $works);
    wtho_write_json('site.json', $site);
    wtho_flash('Startbild: ' . $id);
  } elseif ($action === 'up' && $idx !== null && $idx > 0) {
    [$works[$idx - 1], $works[$idx]] = [$works[$idx], $works[$idx - 1]];
    wtho_write_json('works.json', array_values($works));
    wtho_flash('Reihenfolge gespeichert.');
  } elseif ($action === 'down' && $idx !== null && $idx < count($works) - 1) {
    [$works[$idx + 1], $works[$idx]] = [$works[$idx], $works[$idx + 1]];
    wtho_write_json('works.json', array_values($works));
    wtho_flash('Reihenfolge gespeichert.');
  } elseif ($action === 'delete' && $idx !== null) {
    array_splice($works, $idx, 1);
    if ($hero === $id && $works) {
      wtho_set_hero($site, $works, (string)$works[0]['id']);
    }
    wtho_write_json('works.json', array_values($works));
    wtho_write_json('site.json', $site);
    wtho_flash('Werk aus der Liste genommen (Ordner bleibt als Backup).');
  }
  header('Location: index.php');
  exit;
}

admin_header('Werke', 'index.php');
?>
<h1>Werke</h1>
<p class="muted"><?= count($works) ?> Arbeiten. Das markierte Werk ist das große Bild oben auf der Startseite.</p>
<p class="actions"><a class="btn" href="work.php">Neues Werk</a></p>

<?php foreach ($works as $i => $w):
  $id = (string)($w['id'] ?? '');
  $cover = $w['images'][0] ?? ($id . '.jpg');
  $src = '../works/' . rawurlencode($id) . '/' . rawurlencode((string)$cover);
  $isHero = $id === $hero;
?>
  <div class="work-row">
    <img class="thumb" src="<?= wtho_h($src) ?>" alt="" />
    <div>
      <?php if ($isHero): ?><div class="hero-badge">Startseite</div><?php endif; ?>
      <strong><?= wtho_h((string)($w['title']['de'] ?? $id)) ?></strong>
      <div class="muted"><?= wtho_h($id) ?> · <?= wtho_h((string)($w['year'] ?? '')) ?> · <?= wtho_h((string)($w['size'] ?? '')) ?></div>
    </div>
    <form method="post" class="row">
      <?php admin_csrf_field(); ?>
      <input type="hidden" name="id" value="<?= wtho_h($id) ?>" />
      <button class="btn ghost small" name="action" value="up" <?= $i === 0 ? 'disabled' : '' ?>>↑</button>
      <button class="btn ghost small" name="action" value="down" <?= $i === count($works) - 1 ? 'disabled' : '' ?>>↓</button>
      <?php if (!$isHero): ?>
        <button class="btn ghost small" name="action" value="hero">Startbild</button>
      <?php endif; ?>
      <a class="btn ghost small" href="work.php?id=<?= wtho_h($id) ?>">Bearbeiten</a>
      <button class="btn danger small" name="action" value="delete" onclick="return confirm('Nur aus der Liste nehmen?')">Entfernen</button>
    </form>
  </div>
<?php endforeach; ?>
<?php admin_footer(); ?>
