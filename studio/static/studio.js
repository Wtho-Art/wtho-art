(function () {
  function rowOf(node) {
    return node && node.closest ? node.closest("[data-row]") : null;
  }

  document.addEventListener("click", function (event) {
    var move = event.target.closest("[data-move]");
    if (move) {
      event.preventDefault();
      var row = rowOf(move);
      if (!row || !row.parentElement) return;
      if (move.dataset.move === "up" && row.previousElementSibling) {
        row.parentElement.insertBefore(row, row.previousElementSibling);
      }
      if (move.dataset.move === "down" && row.nextElementSibling) {
        row.parentElement.insertBefore(row.nextElementSibling, row);
      }
      return;
    }
    var remove = event.target.closest("[data-remove-row]");
    if (remove) {
      event.preventDefault();
      var gone = rowOf(remove);
      if (gone) gone.remove();
      return;
    }
    var add = event.target.closest("[data-add]");
    if (add) {
      event.preventDefault();
      var template = document.getElementById(add.dataset.add);
      var target = document.getElementById(add.dataset.target);
      if (template && target) target.appendChild(template.content.cloneNode(true));
    }
  });

  document.querySelectorAll("[data-sortable]").forEach(function (list) {
    var drag = null;
    list.addEventListener("dragstart", function (event) {
      drag = rowOf(event.target);
      if (!drag) return;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", "row");
    });
    list.addEventListener("dragover", function (event) {
      if (!drag) return;
      var over = rowOf(event.target);
      if (!over || over === drag || over.parentElement !== list) return;
      event.preventDefault();
      var rect = over.getBoundingClientRect();
      var after = event.clientY > rect.top + rect.height / 2;
      list.insertBefore(drag, after ? over.nextSibling : over);
    });
    list.addEventListener("dragend", function () { drag = null; });
  });
})();
