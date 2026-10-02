(function () {
  "use strict";
  var form = document.querySelector('[data-nail-form]');
  var list = document.querySelector('[data-photo-list]');
  if (!form || !list) return;
  var edits = {};
  function cards() { return Array.from(list.querySelectorAll('[data-photo-card]')); }
  function active() { return cards().filter(function (card) { return !card.querySelector('[name="remove_images"]').checked; }); }
  function refresh() {
    var remaining = active();
    cards().forEach(function (card) {
      var index = remaining.indexOf(card);
      card.querySelector('[data-photo-label]').textContent = index < 0 ? 'Will be removed' : 'Photo ' + (index + 1) + (index === 0 ? ' — Cover' : '');
      card.querySelector('[data-photo-up]').disabled = index <= 0;
      card.querySelector('[data-photo-down]').disabled = index < 0 || index === remaining.length - 1;
      card.querySelector('[data-photo-cover]').disabled = index <= 0;
    });
  }
  cards().forEach(function (card) {
    var original = card.querySelector('[data-photo-original]');
    var canvas = card.querySelector('[data-crop-preview]');
    var zoom = card.querySelector('[data-crop-zoom]');
    var x = card.querySelector('[data-crop-x]');
    var y = card.querySelector('[data-crop-y]');
    var rotation = 0;
    var changed = false;
    var status = card.querySelector('[data-crop-status]');
    function preview() {
      if (!original.complete || !original.naturalWidth) return;
      var rotated = document.createElement('canvas');
      var swapped = rotation % 180 !== 0;
      rotated.width = swapped ? original.naturalHeight : original.naturalWidth;
      rotated.height = swapped ? original.naturalWidth : original.naturalHeight;
      var context = rotated.getContext('2d');
      context.translate(rotated.width / 2, rotated.height / 2);
      context.rotate(rotation * Math.PI / 180);
      context.drawImage(original, -original.naturalWidth / 2, -original.naturalHeight / 2);
      var side = Math.min(rotated.width, rotated.height) / Number(zoom.value);
      var left = (rotated.width - side) * Number(x.value) / 100;
      var top = (rotated.height - side) * Number(y.value) / 100;
      var target = canvas.getContext('2d');
      target.clearRect(0, 0, canvas.width, canvas.height);
      if (changed) {
        target.drawImage(rotated, left, top, side, side, 0, 0, canvas.width, canvas.height);
      } else {
        var scale = Math.min(canvas.width / rotated.width, canvas.height / rotated.height);
        var displayedWidth = rotated.width * scale;
        var displayedHeight = rotated.height * scale;
        target.drawImage(rotated, (canvas.width - displayedWidth) / 2, (canvas.height - displayedHeight) / 2, displayedWidth, displayedHeight);
      }
      if (changed) {
        edits[card.dataset.path] = {x: left / rotated.width, y: top / rotated.height, width: side / rotated.width, height: side / rotated.height, rotation: rotation};
        status.textContent = 'Crop preview. Changes apply when you save the product.';
      }
    }
    original.addEventListener('load', preview);
    original.addEventListener('error', function () {
      status.textContent = 'Photo could not be loaded. Reload the page before editing.';
      [zoom, x, y, card.querySelector('[data-crop-rotate]')].forEach(function (control) { control.disabled = true; });
    });
    [zoom, x, y].forEach(function (control) { control.addEventListener('input', function () { changed = true; preview(); }); });
    card.querySelector('[data-crop-rotate]').addEventListener('click', function () { rotation = (rotation + 90) % 360; changed = true; preview(); });
    card.querySelector('[data-crop-reset]').addEventListener('click', function () {
      rotation = 0; zoom.value = 1; x.value = 50; y.value = 50; changed = false;
      delete edits[card.dataset.path];
      status.textContent = 'Original photo. Adjust a control to apply a square crop.';
      preview();
    });
    card.querySelector('[data-photo-up]').addEventListener('click', function () {
      var remaining = active(); var index = remaining.indexOf(card);
      if (index > 0) list.insertBefore(card, remaining[index - 1]);
      refresh();
    });
    card.querySelector('[data-photo-down]').addEventListener('click', function () {
      var remaining = active(); var index = remaining.indexOf(card);
      if (index >= 0 && index < remaining.length - 1) list.insertBefore(remaining[index + 1], card);
      refresh();
    });
    card.querySelector('[data-photo-cover]').addEventListener('click', function () { list.insertBefore(card, list.firstChild); refresh(); });
    card.querySelector('[name="remove_images"]').addEventListener('change', refresh);
    preview();
  });
  // Capture runs before the existing submit handler builds its FormData.
  form.addEventListener('submit', function () {
    form.querySelectorAll('[data-photo-payload]').forEach(function (input) { input.remove(); });
    var retainedEdits = {};
    function field(name, value) {
      var input = document.createElement('input'); input.type = 'hidden'; input.name = name; input.value = value;
      input.setAttribute('data-photo-payload', ''); form.appendChild(input);
    }
    active().forEach(function (card) {
      field('image_order', card.dataset.path);
      if (edits[card.dataset.path]) retainedEdits[card.dataset.path] = edits[card.dataset.path];
    });
    field('photo_edits', JSON.stringify(retainedEdits));
  }, true);
  refresh();
})();
