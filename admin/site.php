<?php
declare(strict_types=1);
require __DIR__ . '/inc/bootstrap.php';
require __DIR__ . '/inc/layout.php';
wtho_require_login();

$site = wtho_read_json('site.json');
$works = wtho_read_json('works.json');
$error = '';

$copyKeys = [
  'kicker' => 'Kicker unter dem Namen',
  'heroQuote' => 'Zitat Startseite',
  'heroLead' => 'Lead-Text Startseite',
  'manifestoTitle' => 'Manifest Titel',
  'manifestoBody' => 'Manifest Text',
  'worksLead' => 'Intro über der Galerie',
  'aboutTitle' => 'Atelier-Titel',
  'aboutP1' => 'Über den Künstler 1',
  'aboutP2' => 'Über den Künstler 2',
  'aboutP3' => 'Über den Künstler 3',
  'aboutP4' => 'Über den Künstler 4',
  'aboutQuote' => 'Zitat Atelier',
  'navAbout' => 'Menüpunkt Atelier',
  'contactLead' => 'Kontakt-Intro',
  'contactNote' => 'Hinweis unter dem Formular',
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  wtho_csrf_check();
  try {
    $site['contactEmail'] = trim((string)($_POST['contactEmail'] ?? $site['contactEmail']));
    $site['instagram'] = trim((string)($_POST['instagram'] ?? $site['instagram']));
    $hero = (string)($_POST['heroWorkId'] ?? $site['heroWorkId']);
    if (wtho_find_work($works, $hero) !== null) {
      wtho_set_hero($site, $works, $hero);
    }
    foreach ($copyKeys as $key => $_label) {
      $site['copy']['de'][$key] = (string)($_POST['de'][$key] ?? $site['copy']['de'][$key] ?? '');
      $site['copy']['en'][$key] = (string)($_POST['en'][$key] ?? $site['copy']['en'][$key] ?? '');
    }
    $ex = [];
    foreach ((array)($_POST['ex_year'] ?? []) as $i => $year) {
      $year = trim((string)$year);
      $de = trim((string)($_POST['ex_de'][$i] ?? ''));
      $en = trim((string)($_POST['ex_en'][$i] ?? ''));
      if ($year === '' && $de === '' && $en === '') continue;
      $ex[] = ['year' => $year, 'de' => $de, 'en' => $en];
    }
    $path = [];
    foreach ((array)($_POST['path_year'] ?? []) as $i => $year) {
      $year = trim((string)$year);
      $de = trim((string)($_POST['path_de'][$i] ?? ''));
      $en = trim((string)($_POST['path_en'][$i] ?? ''));
      if ($year === '' && $de === '' && $en === '') continue;
      $path[] = ['year' => $year, 'de' => $de, 'en' => $en];
    }
    $site['exhibits'] = $ex;
    $site['path'] = $path;
    wtho_write_json('site.json', $site);
    wtho_write_json('works.json', $works);
    wtho_flash('Texte gespeichert.');
    header('Location: site.php');
    exit;
  } catch (Throwable $e) {
    $error = $e->getMessage();
  }
}

admin_header('Texte & Ausstellungen', 'site.php');
?>
<h1>Texte & Ausstellungen</h1>
<?php if ($error): ?><p class="error"><?= wtho_h($error) ?></p><?php endif; ?>

<form method="post">
  <?php admin_csrf_field(); ?>

  <label>Großes Startbild</label>
  <select name="heroWorkId">
    <?php foreach ($works as $w): ?>
      <option value="<?= wtho_h((string)$w['id']) ?>" <?= ($site['heroWorkId'] ?? '') === $w['id'] ? 'selected' : '' ?>>
        <?= wtho_h((string)($w['title']['de'] ?? $w['id'])) ?>
      </option>
    <?php endforeach; ?>
  </select>

  <div class="grid2">
    <div>
      <label>Kontakt-E-Mail</label>
      <input type="email" name="contactEmail" value="<?= wtho_h((string)($site['contactEmail'] ?? '')) ?>" />
    </div>
    <div>
      <label>Instagram-URL</label>
      <input type="text" name="instagram" value="<?= wtho_h((string)($site['instagram'] ?? '')) ?>" />
    </div>
  </div>

  <?php foreach ($copyKeys as $key => $label): ?>
    <div class="grid2">
      <div>
        <label><?= wtho_h($label) ?> DE</label>
        <textarea name="de[<?= wtho_h($key) ?>]"><?= wtho_h((string)($site['copy']['de'][$key] ?? '')) ?></textarea>
      </div>
      <div>
        <label><?= wtho_h($label) ?> EN</label>
        <textarea name="en[<?= wtho_h($key) ?>]"><?= wtho_h((string)($site['copy']['en'][$key] ?? '')) ?></textarea>
      </div>
    </div>
  <?php endforeach; ?>

  <h1 style="margin-top:2rem">Ausstellungen</h1>
  <p class="muted">Leere Zeile am Ende = neue Zeile. Komplett leere Zeilen werden verworfen.</p>
  <?php
    $exhibits = $site['exhibits'] ?? [];
    $exhibits[] = ['year' => '', 'de' => '', 'en' => ''];
    foreach ($exhibits as $row):
  ?>
    <div class="repeat">
      <label>Jahr</label>
      <input type="text" name="ex_year[]" value="<?= wtho_h((string)$row['year']) ?>" />
      <label>DE</label>
      <input type="text" name="ex_de[]" value="<?= wtho_h((string)$row['de']) ?>" />
      <label>EN</label>
      <input type="text" name="ex_en[]" value="<?= wtho_h((string)$row['en']) ?>" />
    </div>
  <?php endforeach; ?>

  <h1 style="margin-top:2rem">Werdegang</h1>
  <?php
    $path = $site['path'] ?? [];
    $path[] = ['year' => '', 'de' => '', 'en' => ''];
    foreach ($path as $row):
  ?>
    <div class="repeat">
      <label>Jahr</label>
      <input type="text" name="path_year[]" value="<?= wtho_h((string)$row['year']) ?>" />
      <label>DE</label>
      <input type="text" name="path_de[]" value="<?= wtho_h((string)$row['de']) ?>" />
      <label>EN</label>
      <input type="text" name="path_en[]" value="<?= wtho_h((string)$row['en']) ?>" />
    </div>
  <?php endforeach; ?>

  <p class="actions"><button class="btn" type="submit">Speichern</button></p>
</form>
<?php admin_footer(); ?>
