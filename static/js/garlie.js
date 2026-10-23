(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Toasts ----------------------------------------------------------------
  function toast(message, kind) {
    var box = $(".toasts");
    if (!box) return;
    var el = document.createElement("p");
    el.className = "toast toast-" + (kind || "success");
    el.textContent = message;
    box.appendChild(el);
    setTimeout(function () { el.classList.add("is-leaving"); setTimeout(function () { el.remove(); }, 350); }, 3200);
  }
  $$(".toast").forEach(function (el) {
    setTimeout(function () { el.classList.add("is-leaving"); setTimeout(function () { el.remove(); }, 350); }, 4200);
  });

  // Announcement bar (remembered for the session) -------------------------
  var announce = $("#announce");
  try { if (sessionStorage.getItem("announce-closed")) announce && announce.remove(); } catch (e) {}
  $$("[data-dismiss]").forEach(function (b) {
    b.addEventListener("click", function () {
      var t = document.getElementById(b.dataset.dismiss);
      if (t) t.remove();
      try { sessionStorage.setItem("announce-closed", "1"); } catch (e) {}
    });
  });

  // Mobile nav + search panel ---------------------------------------------
  var menu = $(".menu-toggle"), nav = $("#site-nav");
  if (menu && nav) menu.addEventListener("click", function () {
    var open = nav.classList.toggle("is-open");
    menu.setAttribute("aria-expanded", String(open));
    menu.textContent = open ? "Close" : "Menu";
  });
  $$("[data-toggle]").forEach(function (b) {
    b.addEventListener("click", function () {
      var panel = document.getElementById(b.dataset.toggle);
      panel.hidden = !panel.hidden;
      b.setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden) { var i = $("input", panel); i && i.focus(); }
    });
  });
  var sp = $("#search-panel");
  if (sp && $("#q") && $("#q").value) { sp.hidden = false; }

  // Add to bag without leaving the page -----------------------------------
  function csrfToken(form) { var i = $("input[name=csrfmiddlewaretoken]", form); return i ? i.value : ""; }
  function updateCount(n) { $$("[data-cart-count]").forEach(function (el) { el.textContent = n; }); }

  $$("form[data-cart-add]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.fetch) return;
      e.preventDefault();
      var btn = $("button[type=submit]", form), label = btn && btn.textContent;
      if (btn) { btn.disabled = true; btn.textContent = "Adding..."; }
      fetch(form.action, {
        method: "POST", body: new FormData(form), credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken(form) }
      }).then(function (r) { return r.json(); }).then(function (d) {
        toast(d.message, d.ok ? "success" : "error");
        if (typeof d.count === "number") updateCount(d.count);
      }).catch(function () { form.submit(); })
        .finally(function () { if (btn) { btn.disabled = false; btn.textContent = label; } });
    });
  });

  // Newsletter ------------------------------------------------------------
  $$("form[data-newsletter]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.fetch) return;
      e.preventDefault();
      fetch(form.action, {
        method: "POST", body: new FormData(form), credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken(form) }
      }).then(function (r) { return r.json(); }).then(function (d) {
        toast(d.message, d.ok ? "success" : "error");
        if (d.ok) form.reset();
      }).catch(function () { form.submit(); });
    });
  });

  // Product page: size picker updates price and stock text ----------------
  var pf = $("[data-product-form]");
  if (pf) {
    var price = $("[data-price]", pf), old = $("[data-old-price]", pf), stock = $("[data-stock-text]", pf), qty = $("input[name=qty]", pf);
    $$("input[name=variant]", pf).forEach(function (r) {
      r.addEventListener("change", function () {
        price.textContent = r.dataset.price;
        old.textContent = r.dataset.old || "";
        var n = parseInt(r.dataset.stock, 10);
        stock.textContent = n <= 5 ? "Only " + n + " left" : "In stock";
        if (qty) { qty.max = Math.min(n, 10); if (parseInt(qty.value, 10) > qty.max) qty.value = qty.max; }
      });
    });
  }
})();
