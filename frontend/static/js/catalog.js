/* =========================================================================
   MISS UNIVERSE NAIL ART STUDIO — public interactions
   Progressive enhancement: the catalogue works without JS (plain GET form);
   this script upgrades it to live, no-reload search / filter / sort.
   ========================================================================= */
(function () {
  "use strict";

  /* ---- Mobile navigation ------------------------------------------------ */
  function initNav() {
    var toggle = document.querySelector("[data-nav-toggle]");
    var nav = document.querySelector("[data-nav]");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---- WhatsApp quick-message form -------------------------------------- */
  function initWhatsAppForm() {
    var form = document.querySelector("[data-wa-form]");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var number = (form.getAttribute("data-wa-number") || "").replace(/\D/g, "");
      var name = (form.elements.name && form.elements.name.value || "").trim();
      var message = (form.elements.message && form.elements.message.value || "").trim();
      var parts = [];
      if (name) parts.push("Hi, I'm " + name + ".");
      parts.push(message || "I have a nail art enquiry.");
      var text = parts.join(" ");
      var url = "https://wa.me/" + number + "?text=" + encodeURIComponent(text);
      window.open(url, "_blank", "noopener");
    });
  }

  /* ---- Live catalogue --------------------------------------------------- */
  function initCatalog() {
    var form = document.querySelector("[data-catalog-form]");
    var results = document.querySelector("[data-results]");
    var pager = document.querySelector("[data-pagination]");
    var meta = document.querySelector("[data-catalog-meta]");
    if (!form || !results) return;

    var searchEl = form.querySelector("[data-catalog-search]");
    var categoryEl = form.querySelector("[data-catalog-category]");
    var sortEl = form.querySelector("[data-catalog-sort]");

    var state = readStateFromUrl();
    var reqToken = 0;

    function readStateFromUrl() {
      var p = new URLSearchParams(window.location.search);
      return {
        search: p.get("search") || "",
        category: p.get("category") || "",
        sort: p.get("sort") || (sortEl ? sortEl.value : "newest"),
        page: parseInt(p.get("page"), 10) || 1
      };
    }

    function buildQuery(includePage) {
      var p = new URLSearchParams();
      if (state.search) p.set("search", state.search);
      if (state.category) p.set("category", state.category);
      if (state.sort) p.set("sort", state.sort);
      if (includePage && state.page > 1) p.set("page", state.page);
      return p;
    }

    function esc(s) {
      var d = document.createElement("div");
      d.textContent = s == null ? "" : String(s);
      return d.innerHTML;
    }

    function truncate(s, n) {
      s = s || "";
      if (s.length <= n) return s;
      var cut = s.slice(0, n);
      var sp = cut.lastIndexOf(" ");
      if (sp > 0) cut = cut.slice(0, sp);
      return cut + "...";
    }

    function cardHtml(nail) {
      var href = "/nail/" + encodeURIComponent(nail.slug);
      var media = nail.image_url
        ? '<img src="' + esc(nail.image_url) + '" alt="' + esc(nail.image_alt || nail.name) +
          '" loading="lazy" decoding="async" width="600" height="600">'
        : '<span class="card__placeholder" aria-hidden="true">' + esc((nail.name || "?").charAt(0).toUpperCase()) + "</span>";
      var chip = nail.category
        ? '<span class="card__chip">' + esc(nail.category.name) + "</span>"
        : "";
      return (
        '<article class="card">' +
          '<a class="card__media" href="' + href + '" aria-label="View ' + esc(nail.name) + '">' +
            media + chip +
          "</a>" +
          '<div class="card__body">' +
            '<h3 class="card__title"><a href="' + href + '">' + esc(nail.name) + "</a></h3>" +
            '<p class="card__desc">' + esc(truncate(nail.description, 80)) + "</p>" +
            '<div class="card__foot">' +
              '<span class="card__price">' + esc(nail.price_display) + "</span>" +
              '<a class="btn btn--ghost btn--sm" href="' + href + '">View Details</a>' +
            "</div>" +
          "</div>" +
        "</article>"
      );
    }

    function emptyHtml() {
      return (
        '<div class="state state--empty">' +
          '<span class="state__icon" aria-hidden="true">✦</span>' +
          "<h3>No nail designs found.</h3>" +
          "<p>Try a different search or category.</p>" +
          '<a href="/catalog" class="btn btn--outline btn--sm" data-clear-filters>Clear Filters</a>' +
        "</div>"
      );
    }

    function paginationHtml(data) {
      if (data.pages <= 1) return "";
      var base = buildQuery(false);
      function item(page, label, opts) {
        opts = opts || {};
        if (opts.disabled) return '<span class="pagination__item is-disabled">' + label + "</span>";
        var q = new URLSearchParams(base);
        if (page > 1) q.set("page", page);
        var qs = q.toString();
        return '<a class="pagination__item' + (opts.active ? " is-active" : "") +
          '" data-page="' + page + '" href="/catalog' + (qs ? "?" + qs : "") + '">' + label + "</a>";
      }
      var html = '<nav class="pagination" aria-label="Catalogue pages">';
      html += item(data.page - 1, "‹ Prev", { disabled: !data.has_prev });
      for (var i = 1; i <= data.pages; i++) html += item(i, String(i), { active: i === data.page });
      html += item(data.page + 1, "Next ›", { disabled: !data.has_next });
      html += "</nav>";
      return html;
    }

    function render(data) {
      if (data.items && data.items.length) {
        var grid = '<div class="grid grid--cards">';
        for (var i = 0; i < data.items.length; i++) grid += cardHtml(data.items[i]);
        grid += "</div>";
        results.innerHTML = grid;
      } else {
        results.innerHTML = emptyHtml();
      }
      if (pager) pager.innerHTML = paginationHtml(data);
      if (meta) {
        meta.innerHTML = data.total
          ? "Showing <strong>" + data.items.length + "</strong> of <strong>" + data.total +
            "</strong> design" + (data.total === 1 ? "" : "s")
          : "";
      }
    }

    function fetchCatalog(pushHistory) {
      var token = ++reqToken;
      var query = buildQuery(true);
      results.classList.add("is-loading");
      fetch("/api/nail-arts?" + query.toString(), { headers: { Accept: "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error("Request failed");
          return r.json();
        })
        .then(function (data) {
          if (token !== reqToken) return; // a newer request superseded this one
          render(data);
          if (pushHistory !== false) {
            var url = "/catalog" + (query.toString() ? "?" + query.toString() : "");
            window.history.pushState({ catalog: true }, "", url);
          }
        })
        .catch(function () {
          if (token !== reqToken) return;
          results.innerHTML =
            '<div class="state"><span class="state__icon">!</span><h3>Something went wrong.</h3>' +
            '<p>Please try again.</p></div>';
        })
        .finally(function () {
          results.classList.remove("is-loading");
        });
    }

    var debouncedSearch = debounce(function () {
      state.search = searchEl ? searchEl.value.trim() : "";
      state.page = 1;
      fetchCatalog();
    }, 300);

    if (searchEl) searchEl.addEventListener("input", debouncedSearch);
    if (categoryEl)
      categoryEl.addEventListener("change", function () {
        state.category = categoryEl.value;
        state.page = 1;
        fetchCatalog();
      });
    if (sortEl)
      sortEl.addEventListener("change", function () {
        state.sort = sortEl.value;
        state.page = 1;
        fetchCatalog();
      });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      state.search = searchEl ? searchEl.value.trim() : "";
      state.category = categoryEl ? categoryEl.value : "";
      state.sort = sortEl ? sortEl.value : state.sort;
      state.page = 1;
      fetchCatalog();
    });

    // Pagination (event-delegated; links still work if JS is off)
    if (pager)
      pager.addEventListener("click", function (e) {
        var link = e.target.closest("a.pagination__item");
        if (!link) return;
        e.preventDefault();
        state.page = parseInt(link.getAttribute("data-page"), 10) || 1;
        fetchCatalog();
        window.scrollTo({ top: form.offsetTop - 90, behavior: "smooth" });
      });

    // Clear filters (delegated because the empty-state button is re-rendered)
    results.addEventListener("click", function (e) {
      var clear = e.target.closest("[data-clear-filters]");
      if (!clear) return;
      e.preventDefault();
      state = { search: "", category: "", sort: state.sort, page: 1 };
      if (searchEl) searchEl.value = "";
      if (categoryEl) categoryEl.value = "";
      fetchCatalog();
    });

    window.addEventListener("popstate", function () {
      state = readStateFromUrl();
      if (searchEl) searchEl.value = state.search;
      if (categoryEl) categoryEl.value = state.category;
      if (sortEl) sortEl.value = state.sort;
      fetchCatalog(false);
    });
  }

  function debounce(fn, wait) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNav();
    initWhatsAppForm();
    initCatalog();
  });
})();
