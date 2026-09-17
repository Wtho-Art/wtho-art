<?php
declare(strict_types=1);
require __DIR__ . '/inc/bootstrap.php';
require __DIR__ . '/inc/layout.php';
wtho_require_login();

$works = wtho_read_json('works.json');
$site = wtho_read_json('site.json');
$id = (string)($_GET['id'] ?? $_POST['id'] ?? '');
$idx = $id !== '' ? wtho_find_work($works, $id) : null;
$creating = $idx === null;

$work = $creating ? [
  'id' => '',
  'year' => date('Y'),
  'size' => '',
  'layout' => 'portrait',
  'span' => false,
  'hero' => false,
  'images' => [],
  'title' => ['de' => '', 'en' => ''],
  'medium' => ['de' => 'Öl auf Leinwand', 'en' => 'Oil on canvas'],
  'statement' => ['de' => '', 'en' => ''],
] : $works[$idx];

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  wtho_csrf_check();
  try {
    $titleDe = trim((string)($_POST['title_de'] ?? ''));
    $titleEn = trim((string)($_POST['title_en'] ?? ''));
    $newId = $creating ? wtho_slug((string)($_POST['id'] ?? $titleEn ?: $titleDe)) : $id;
    if ($newId === '' || $newId === 'work') {
      throw new RuntimeException('Bitte eine ID oder einen Titel angeben.');
    }
    if ($creating && wtho_find_work($works, $newId) !== null) {
      throw new RuntimeException('Diese ID gibt es schon.');
    }

    $work['id'] = $newId;
    $work['year'] = trim((string)($_POST['year'] ?? ''));
    $work['size'] = trim((string)($_POST['size'] ?? ''));
    $work['layout'] = ($_POST['layout'] ?? 'portrait') === 'landscape' ? 'landscape' : 'portrait';
    $work['span'] = !empty($_POST['span']);
    $work['title'] = ['de' => $titleDe ?: $titleEn, 'en' => $titleEn ?: $titleDe];
    $work['medium'] = [
      'de' => trim((string)($_POST['medium_de'] ?? '')),
      'en' => trim((string)($_POST['medium_en'] ?? '')),
    ];
    $work['statement'] = [
      'de' => trim((string)($_POST['statement_de'] ?? '')),
      'en' => trim((string)($_POST['statement_en'] ?? '')),
    ];

    $images = $work['images'] ?? [];
    foreach ((array)($_POST['delete_image'] ?? []) as $rm) {
      $rm = basename((string)$rm);
      $images = array_values(array_filter($images, fn($n) => $n !== $rm));
    }
    if (!empty($_FILES['cover']['name'])) {
      $saved = wtho_save_upload($newId, $_FILES['cover']);
      if ($saved) array_unshift($images, $saved);
    }
    if (!empty($_FILES['extra']['name'])) {
      $saved = wtho_save_upload($newId, $_FILES['extra']);
      if ($saved) $images[] = $saved;
    }
    $work['images'] = array_values(array_unique(array_filter($images)));

    if ($creating) {
      $works[] = $work;
    } else {
      $works[$idx] = $work;
    }
    if (!empty($_POST['make_hero'])) {
      wtho_set_hero($site, $works, $newId);
    }
    wtho_ensure_work_page($newId, $work);
    wtho_write_json('works.json', array_values($works));
    wtho_write_json('site.json', $site);
    wtho_flash($creating ? 'Werk angelegt.' : 'Gespeichert.');
    header('Location: work.php?id=' . rawurlencode($newId));
    exit;
  } catch (Throwable $e) {
    $error = $e->getMessage();
    $id = $work['id'] ?? $id;
  }
}

admin_header($creating ? 'Neues Werk' : 'Werk bearbeiten', 'index.php');
?>
<p><a href="index.php">← Alle Werke</a></p>
<h1><?= $creating ? 'Neues Werk' : wtho_h((string)$work['title']['de']) ?></h1>
<?php if ($error): ?><p class="error"><?= wtho_h($error) ?></p><?php endif; ?>

<form method="post" enctype="multipart/form-data">
  <?php admin_csrf_field(); ?>
  <?php if (!$creating): ?>
    <input type="hidden" name="id" value="<?= wtho_h((string)$work['id']) ?>" />
  <?php endif; ?>

  <?php if ($creating): ?>
    <label>Ordner-ID (klein, Bindestriche, z. B. dance-of-duality)</label>
    <input type="text" name="id" value="<?= wtho_h((string)$work['id']) ?>" placeholder="wird aus dem Titel erzeugt, wenn leer" />
  <?php else: ?>
    <p class="muted">ID: <?= wtho_h((string)$work['id']) ?></p>
  <?php endif; ?>

  <div class="grid2">
    <div>
      <label>Titel DE</label>
      <input type="text" name="title_de" value="<?= wtho_h((string)$work['title']['de']) ?>" required />
    </div>
    <div>
      <label>Titel EN</label>
      <input type="text" name="title_en" value="<?= wtho_h((string)$work['title']['en']) ?>" required />
    </div>
    <div>
      <label>Jahr</label>
      <input type="text" name="year" value="<?= wtho_h((string)$work['year']) ?>" />
    </div>
    <div>
      <label>Maß</label>
      <input type="text" name="size" value="<?= wtho_h((string)$work['size']) ?>" placeholder="100 × 70 cm" />
    </div>
    <div>
      <label>Technik DE</label>
      <input type="text" name="medium_de" value="<?= wtho_h((string)$work['medium']['de']) ?>" />
    </div>
    <div>
      <label>Technik EN</label>
      <input type="text" name="medium_en" value="<?= wtho_h((string)$work['medium']['en']) ?>" />
    </div>
  </div>

  <label>Statement DE</label>
  <textarea name="statement_de"><?= wtho_h((string)$work['statement']['de']) ?></textarea>
  <label>Statement EN</label>
  <textarea name="statement_en"><?= wtho_h((string)$work['statement']['en']) ?></textarea>

  <div class="grid2">
    <div>
      <label>Format</label>
      <select name="layout">
        <option value="portrait" <?= ($work['layout'] ?? '') === 'portrait' ? 'selected' : '' ?>>Hochformat</option>
        <option value="landscape" <?= ($work['layout'] ?? '') === 'landscape' ? 'selected' : '' ?>>Querformat</option>
      </select>
    </div>
    <div>
      <label>&nbsp;</label>
      <label style="text-transform:none;letter-spacing:0;font-size:1rem;color:inherit">
        <input type="checkbox" name="span" value="1" <?= !empty($work['span']) ? 'checked' : '' ?> />
        In der Galerie breiter
      </label>
      <label style="text-transform:none;letter-spacing:0;font-size:1rem;color:inherit">
        <input type="checkbox" name="make_hero" value="1" <?= (($site['heroWorkId'] ?? '') === ($work['id'] ?? '')) ? 'checked' : '' ?> />
        Großes Bild auf der Startseite
      </label>
    </div>
  </div>

  <label>Bilder</label>
  <div class="pics">
    <?php foreach ($work['images'] ?? [] as $n): ?>
      <label class="pic">
        <img src="../works/<?= wtho_h((string)$work['id']) ?>/<?= wtho_h((string)$n) ?>" alt="" />
        <span class="muted"><?= wtho_h((string)$n) ?></span><br />
        <input type="checkbox" name="delete_image[]" value="<?= wtho_h((string)$n) ?>" /> löschen
      </label>
    <?php endforeach; ?>
  </div>
  <label>Neues Titelbild (wird zuerst gezeigt)</label>
  <input type="file" name="cover" accept="image/jpeg,image/png,image/webp" />
  <label>Weiteres Bild (Detail)</label>
  <input type="file" name="extra" accept="image/jpeg,image/png,image/webp" />
  <p class="muted">Web-JPEG, lange Kante etwa 1600–2400 px, unter 8 MB. Originale nicht hier hochladen.</p>

  <p class="actions">
    <button class="btn" type="submit">Speichern</button>
    <?php if (!$creating): ?>
      <a class="btn ghost" href="../works/<?= wtho_h((string)$work['id']) ?>/" target="_blank" rel="noopener">Vorschau</a>
    <?php endif; ?>
  </p>
</form>
<?php admin_footer(); ?>
