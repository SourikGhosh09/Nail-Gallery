document.querySelectorAll('[data-product-photo]').forEach(function (link) {
  link.addEventListener('click', function (event) {
    event.preventDefault();
    var photo = document.getElementById('product-photo');
    photo.src = link.href;
    photo.alt = link.querySelector('img').alt;
    document.querySelectorAll('[data-product-photo]').forEach(function (item) {
      item.setAttribute('aria-current', item === link ? 'true' : 'false');
    });
  });
});
