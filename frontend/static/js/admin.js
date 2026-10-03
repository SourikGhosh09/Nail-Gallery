/* =========================================================================
   MISS UNIVERSE NAIL ART STUDIO — admin panel
   Handles auth, CRUD (multipart), CSRF, image preview, status toggles,
   safe category deletion, toasts and the confirmation modal.
   ========================================================================= */
(function () {
  "use strict";

  var API = "/api";

  /* ---- Small helpers ---------------------------------------------------- */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function getCookie(name) {
    var m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? decodeURIComponent(m.pop()) : "";
  }

  // Unified fetch wrapper. Adds CSRF header on mutating requests and always
  // resolves to { ok, status, body }.
  function api(method, url, opts) {
    opts = opts || {};
    var headers = { Accept: "application/json" };
    if (method !== "GET" && method !== "HEAD") headers["X-CSRF-Token"] = getCookie("csrf_token");
    var init = { method: method, headers: headers, credentials: "same-origin" };
    if (opts.json) { headers["Content-Type"] = "application/json"; init.body = JSON.stringify(opts.json); }
    else if (opts.form) { init.body = opts.form; }
    return fetch(url, init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        return { ok: res.ok, status: res.status, body: body };
      });
    });
  }

  // Normalise the many shapes `detail` can take into one object.
  function parseError(res) {
    var d = res.body && res.body.detail;
    var out = { message: "Something went wrong. Please try again.", errors: {}, requires_action: false, data: null };
    if (typeof d === "string") out.message = d;
    else if (d && typeof d === "object") {
      out.message = d.message || out.message;
      out.errors = d.errors || {};
      out.requires_action = !!d.requires_action;
      out.data = d;
    }
    return out;
  }

  function setLoading(btn, on, text) {
    if (!btn) return;
    if (on) {
      if (!btn.dataset.orig) btn.dataset.orig = btn.textContent;
      if (text) btn.textContent = text;
      btn.disabled = true;
    } else {
      if (btn.dataset.orig) btn.textContent = btn.dataset.orig;
      btn.disabled = false;
    }
  }

  function showError(box, msg) { if (box) { box.textContent = msg; box.hidden = false; } }
  function hideError(box) { if (box) { box.hidden = true; box.textContent = ""; } }

  function clearFieldErrors(form) {
    $all("[data-error-for]", form).forEach(function (s) { s.textContent = ""; });
    $all(".field.has-error", form).forEach(function (f) { f.classList.remove("has-error"); });
    hideError($("[data-form-error]", form));
  }

  function setFieldError(form, field, msg) {
    var span = $('[data-error-for="' + field + '"]', form);
    if (span) {
      span.textContent = msg;
      var f = span.closest(".field");
      if (f) f.classList.add("has-error");
    }
  }

  function applyFormErrors(form, res) {
    var err = parseError(res);
    var keys = Object.keys(err.errors);
    keys.forEach(function (field) { setFieldError(form, field, err.errors[field]); });
    var box = $("[data-form-error]", form);
    // Show a summary unless every error was mapped to a visible field.
    if (box && (!keys.length || err.message)) showError(box, err.message);
  }

  /* ---- Toasts + flash across reloads ------------------------------------ */
  function toast(msg, type) {
    var wrap = $("[data-toast-wrap]");
    if (!wrap) return;
    var t = document.createElement("div");
    t.className = "toast" + (type === "ok" ? " toast--ok" : type === "err" ? " toast--err" : "");
    t.textContent = msg;
    wrap.appendChild(t);
    setTimeout(function () {
      t.classList.add("is-leaving");
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 320);
    }, 3200);
  }

  function flash(msg, type) {
    try { sessionStorage.setItem("admin_flash", JSON.stringify({ msg: msg, type: type })); } catch (e) {}
  }
  function flashReload(msg, type) { flash(msg, type); window.location.reload(); }
  function consumeFlash() {
    try {
      var raw = sessionStorage.getItem("admin_flash");
      if (raw) { sessionStorage.removeItem("admin_flash"); var f = JSON.parse(raw); toast(f.msg, f.type); }
    } catch (e) {}
  }

  /* ---- Modal ------------------------------------------------------------ */
  function openModal(cfg) {
    var modal = $("[data-modal]");
    if (!modal) return;
    $("[data-modal-title]", modal).textContent = cfg.title || "Confirm";
    $("[data-modal-body]", modal).innerHTML = cfg.body || "";
    var wrap = $("[data-modal-actions]", modal);
    wrap.innerHTML = "";
    (cfg.actions || []).forEach(function (a) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = a.cls || "btn btn--ghost";
      b.textContent = a.label;
      b.addEventListener("click", function () {
        if (a.onClick) a.onClick(b);
        if (a.close) closeModal();
      });
      wrap.appendChild(b);
    });
    modal.hidden = false;
    document.addEventListener("keydown", escClose);
  }
  function closeModal() {
    var modal = $("[data-modal]");
    if (modal) modal.hidden = true;
    document.removeEventListener("keydown", escClose);
  }
  function escClose(e) { if (e.key === "Escape") closeModal(); }

  /* ---- Auth ------------------------------------------------------------- */
  function initLogin() {
    var form = $("[data-login-form]");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var box = $("[data-form-error]", form);
      var btn = $("[data-login-submit]", form);
      hideError(box);
      var email = form.elements.email.value.trim();
      var password = form.elements.password.value;
      if (!email || !password) { showError(box, "Please enter your e-mail and password."); return; }
      setLoading(btn, true, "Signing in…");
      api("POST", API + "/auth/login", { json: { email: email, password: password } })
        .then(function (res) {
          if (res.ok) { window.location.href = "/admin/dashboard"; }
          else { showError(box, parseError(res).message); setLoading(btn, false); }
        })
        .catch(function () { showError(box, "Network error. Please try again."); setLoading(btn, false); });
    });
  }

  function initLogout() {
    $all("[data-logout]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setLoading(btn, true, "Logging out…");
        api("POST", API + "/auth/logout", {}).then(function () { window.location.href = "/admin"; })
          .catch(function () { window.location.href = "/admin"; });
      });
    });
  }

  /* ---- Image drop / preview -------------------------------------------- */
  function initImageDrop(scope) {
    var drop = $("[data-image-drop]", scope);
    if (!drop) return;
    var input = $("[data-image-input]", drop);
    var preview = $("[data-image-preview]", drop);
    var hint = $("[data-image-hint]", drop);
    if (!input) return;

    input.addEventListener("change", function () {
      var previews = $("[data-photo-previews]", scope);
      if (previews) {
        previews.innerHTML = "";
        Array.prototype.forEach.call(input.files || [], function (file) {
          var reader = new FileReader();
          reader.onload = function (ev) {
            var img = document.createElement("img");
            img.src = ev.target.result;
            img.alt = file.name;
            img.width = 100;
            img.height = 100;
            previews.appendChild(img);
          };
          reader.readAsDataURL(file);
        });
      }
      var file = input.files && input.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (ev) {
        if (preview) { preview.src = ev.target.result; preview.hidden = false; }
        if (hint) hint.hidden = true;
      };
      reader.readAsDataURL(file);
    });

    ["dragenter", "dragover"].forEach(function (t) {
      drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.add("is-drag"); });
    });
    ["dragleave", "drop"].forEach(function (t) {
      drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.remove("is-drag"); });
    });
    drop.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event("change"));
      }
    });
  }

  /* ---- Nail-art form ---------------------------------------------------- */
  function initNailForm() {
    var form = $("[data-nail-form]");
    if (!form) return;
    initImageDrop(form);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      clearFieldErrors(form);
      var id = form.getAttribute("data-nail-id");
      var btn = $("[data-submit]", form);
      var method = id ? "PUT" : "POST";
      var url = API + "/admin/nail-arts" + (id ? "/" + id : "");
      var payload = new FormData(form);
      // Vercel limits the whole request, including all photos and form fields.
      if (form.hasAttribute("data-serverless")) {
        var totalBytes = 0;
        payload.forEach(function (value) {
          totalBytes += value instanceof Blob ? value.size : new Blob([String(value)]).size;
        });
        if (totalBytes > 4 * 1024 * 1024) {
          showError($("[data-form-error]", form), "These photos exceed the 4 MB upload limit. Choose fewer or smaller photos, save, then add the rest.");
          return;
        }
      }
      setLoading(btn, true, "Saving…");
      api(method, url, { form: payload }).then(function (res) {
        if (res.ok) { flash(id ? "Nail art updated." : "Nail art created.", "ok"); window.location.href = "/admin/nail-arts"; }
        else { applyFormErrors(form, res); setLoading(btn, false); }
      }).catch(function () { showError($("[data-form-error]", form), "Network error. Please try again."); setLoading(btn, false); });
    });
  }

  /* ---- Category form ---------------------------------------------------- */
  function initCategoryForm() {
    var form = $("[data-category-form]");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      clearFieldErrors(form);
      var id = form.getAttribute("data-category-id");
      var btn = $("[data-submit]", form);
      var method = id ? "PUT" : "POST";
      var url = API + "/admin/categories" + (id ? "/" + id : "");
      setLoading(btn, true, "Saving…");
      api(method, url, { form: new FormData(form) }).then(function (res) {
        if (res.ok) { flash(id ? "Category updated." : "Category created.", "ok"); window.location.href = "/admin/categories"; }
        else { applyFormErrors(form, res); setLoading(btn, false); }
      }).catch(function () { showError($("[data-form-error]", form), "Network error. Please try again."); setLoading(btn, false); });
    });
  }

  /* ---- Row actions (status + delete) ------------------------------------ */
  function toggleStatus(btn, kind, id, status) {
    setLoading(btn, true, "…");
    api("PATCH", API + "/admin/" + kind + "/" + id + "/status?status=" + encodeURIComponent(status), {})
      .then(function (res) {
        if (res.ok) flashReload(status === "active" ? "Restored." : "Deactivated.", "ok");
        else { toast(parseError(res).message, "err"); setLoading(btn, false); }
      })
      .catch(function () { toast("Network error.", "err"); setLoading(btn, false); });
  }

  function confirmNailDelete(id, name) {
    openModal({
      title: "Delete nail art?",
      body: "<p>This permanently deletes <strong>" + esc(name) + "</strong> and its image. This cannot be undone.</p>" +
            "<p>Tip: use <strong>Deactivate</strong> if you only want to hide it from the site.</p>",
      actions: [
        { label: "Cancel", cls: "btn btn--ghost", close: true },
        { label: "Delete permanently", cls: "btn btn--danger", onClick: function () {
            api("DELETE", API + "/admin/nail-arts/" + id + "?hard=true", {}).then(function (res) {
              if (res.ok) flashReload("Nail art deleted.", "ok");
              else { toast(parseError(res).message, "err"); closeModal(); }
            });
          } }
      ]
    });
  }

  function confirmCategoryDelete(id, name, count) {
    if (count === 0) {
      openModal({
        title: "Delete category?",
        body: "<p>Delete <strong>" + esc(name) + "</strong>? It has no designs, so this is safe.</p>",
        actions: [
          { label: "Cancel", cls: "btn btn--ghost", close: true },
          { label: "Delete", cls: "btn btn--danger", onClick: function () {
              api("DELETE", API + "/admin/categories/" + id, {}).then(function (res) {
                if (res.ok) flashReload("Category deleted.", "ok");
                else { toast(parseError(res).message, "err"); closeModal(); }
              });
            } }
        ]
      });
      return;
    }
    // Category has designs — never orphan them. Offer reassign / deactivate.
    api("GET", API + "/admin/categories", {}).then(function (res) {
      var cats = (res.body && res.body.items) || [];
      var others = cats.filter(function (c) { return String(c.id) !== String(id); });
      var selectHtml = others.length
        ? '<label class="field field--block"><span class="field__label">Move designs to</span>' +
          '<select data-reassign-target>' +
          others.map(function (c) { return '<option value="' + c.id + '">' + esc(c.name) + "</option>"; }).join("") +
          "</select></label>"
        : "<p><em>No other category exists yet. Create one first, or deactivate this category instead.</em></p>";
      var actions = [{ label: "Cancel", cls: "btn btn--ghost", close: true }];
      actions.push({ label: "Deactivate instead", cls: "btn btn--outline", onClick: function () {
        api("DELETE", API + "/admin/categories/" + id + "?action=deactivate", {}).then(function (r) {
          if (r.ok) flashReload("Category deactivated — its designs are hidden but kept.", "ok");
          else { toast(parseError(r).message, "err"); closeModal(); }
        });
      } });
      if (others.length) {
        actions.push({ label: "Move & delete", cls: "btn btn--danger", onClick: function () {
          var sel = $("[data-reassign-target]");
          var target = sel ? sel.value : "";
          if (!target) { toast("Choose a category to move designs into.", "err"); return; }
          api("DELETE", API + "/admin/categories/" + id + "?action=reassign&target_category_id=" + encodeURIComponent(target), {})
            .then(function (r) {
              if (r.ok) flashReload("Designs moved and category deleted.", "ok");
              else { toast(parseError(r).message, "err"); closeModal(); }
            });
        } });
      }
      openModal({
        title: "This category has designs",
        body: "<p><strong>" + esc(name) + "</strong> contains <strong>" + count +
              "</strong> design(s). Choose what happens to them so none is left without a category:</p>" + selectHtml,
        actions: actions
      });
    });
  }

  function initRowActions() {
    document.addEventListener("click", function (e) {
      var el = e.target.closest("[data-action]");
      if (!el) return;
      var action = el.getAttribute("data-action");
      var id = el.getAttribute("data-id");
      var name = el.getAttribute("data-name") || "this item";
      if (action === "nail-status") { e.preventDefault(); toggleStatus(el, "nail-arts", id, el.getAttribute("data-status")); }
      else if (action === "cat-status") { e.preventDefault(); toggleStatus(el, "categories", id, el.getAttribute("data-status")); }
      else if (action === "nail-delete") { e.preventDefault(); confirmNailDelete(id, name); }
      else if (action === "cat-delete") { e.preventDefault(); confirmCategoryDelete(id, name, parseInt(el.getAttribute("data-count"), 10) || 0); }
    });
  }

  /* ---- Layout chrome ---------------------------------------------------- */
  function initChrome() {
    var sideToggle = $("[data-side-toggle]");
    var side = $("[data-admin-side]");
    if (sideToggle && side) sideToggle.addEventListener("click", function () { side.classList.toggle("is-open"); });
    var mc = $("[data-modal-close]");
    if (mc) mc.addEventListener("click", closeModal);
  }

  /* ---- Boot ------------------------------------------------------------- */
  document.addEventListener("DOMContentLoaded", function () {
    initChrome();
    initLogin();
    initLogout();
    initNailForm();
    initCategoryForm();
    initRowActions();
    consumeFlash();
  });
})();
