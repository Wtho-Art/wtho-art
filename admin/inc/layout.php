<?php
declare(strict_types=1);

function admin_header(string $title, string $active = ''): void {
  $flash = wtho_flash();
  echo '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8" />';
  echo '<meta name="viewport" content="width=device-width, initial-scale=1" />';
  echo '<title>' . wtho_h($title) . ' — wtho.art Admin</title>';
  echo '<link rel="stylesheet" href="assets/admin.css" />';
  echo '</head><body>';
  echo '<header class="top">';
  echo '<a class="brand" href="index.php">wtho.art Admin</a>';
  echo '<nav>';
  $links = ['index.php' => 'Werke', 'site.php' => 'Texte & Ausstellungen'];
  foreach ($links as $href => $label) {
    $on = $active === $href ? ' class="on"' : '';
    echo "<a href=\"$href\"$on>" . wtho_h($label) . '</a>';
  }
  echo '<a href="/" target="_blank" rel="noopener">Seite ansehen</a>';
  echo '<a href="logout.php">Abmelden</a>';
  echo '</nav></header>';
  echo '<main class="wrap">';
  if ($flash) echo '<p class="flash">' . wtho_h($flash) . '</p>';
}

function admin_footer(): void {
  echo '</main></body></html>';
}

function admin_csrf_field(): void {
  echo '<input type="hidden" name="csrf" value="' . wtho_h(wtho_csrf_token()) . '" />';
}
