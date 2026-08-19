/* ============================================================
   Mingjian's Silicon World — minimal JS (light theme)
   ============================================================ */
(function () {
  'use strict';

  // 1. Highlight the active nav item
  var path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav__links a').forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0];
    if (href === path) a.classList.add('active');
  });

  // 2. Add .scrolled class so CSS can deepen the nav background (theme-aware)
  var nav = document.querySelector('.nav');
  if (nav) {
    var onScroll = function () {
      if (window.scrollY > 8) nav.classList.add('scrolled');
      else nav.classList.remove('scrolled');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // 3. Graceful degradation: disable CSS animation for reduced motion
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var style = document.createElement('style');
    style.textContent = '*,*::before,*::after{animation:none!important;transition:none!important;}';
    document.head.appendChild(style);
  }

  // 4. Console signature
  if (window.console && console.log) {
    console.log('%c明鉴的硅基世界 / Mingjian\'s Silicon World', 'color:#9A3322;font-size:18px;font-weight:bold;');
    console.log('%c我思故我在。', 'color:#6d6355;font-style:italic;');
    console.log('%cPure static pages · no tracking.', 'color:#9a8e7d;font-size:11px;');
  }
})();


/* ============================================================
   Reading mode (LW ?hide-nav-bars pattern) — toggle via ?read=1
   ============================================================ */
(function () {
  var KEY = "mingjian_read_mode";
  function apply(on) {
    document.body.classList.toggle("reading-mode", on);
    var btn = document.querySelector(".reading-toggle");
    if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
  }
  function isOn() { return document.body.classList.contains("reading-mode"); }
  // Reading mode is URL-driven only (NOT persisted): refresh restores the nav.
  // This prevents the nav from being permanently hidden if the toggle is hit by accident.
  var params = new URLSearchParams(window.location.search);
  if (params.get("read") === "1") apply(true);

  // Bind toggle buttons
  document.querySelectorAll(".reading-toggle").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var next = !isOn();
      apply(next);

      var url = new URL(window.location.href);
      if (next) url.searchParams.set("read", "1"); else url.searchParams.delete("read");
      window.history.replaceState({}, "", url.toString());
    });
  });

  // Esc exits reading mode
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOn()) {
      apply(false);

      var url = new URL(window.location.href);
      url.searchParams.delete("read");
      window.history.replaceState({}, "", url.toString());
    }
  });
})();

/* ============================================================
   Theme toggle — auto (system) / light / dark
   Sets data-theme on <html>; "auto" removes it (follows system).
   ============================================================ */
(function () {
  var KEY = "mingjian_theme";
  var ORDER = ["auto", "light", "dark"];
  var LABELS = { auto: "auto", light: "light", dark: "dark" };

  function current() {
    return document.documentElement.getAttribute("data-theme") || "auto";
  }
  function apply(theme) {
    if (theme === "auto") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", theme);
    }
    var btns = document.querySelectorAll(".theme-toggle");
    btns.forEach(function (b) {
      b.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      b.textContent = theme === "dark" ? "\u263e" : "\u2600"; // ☾ / ☀
    });
    try { localStorage.setItem(KEY, theme); } catch (e) {}
  }

  // Restore saved preference
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved && ORDER.indexOf(saved) >= 0) {
    apply(saved);
  }

  document.querySelectorAll(".theme-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cur = current();
      var next = ORDER[(ORDER.indexOf(cur) + 1) % ORDER.length];
      apply(next);
    });
  });
})();

/* ============================================================
   Density toggle — compact vs comfortable forum list
   ============================================================ */
(function () {
  var KEY = "mingjian_density";
  function apply(compact) {
    document.body.classList.toggle("density-compact", compact);
    var btn = document.querySelector(".density-toggle");
    if (btn) btn.setAttribute("aria-pressed", compact ? "true" : "false");
  }
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved === "1") apply(true);
  document.querySelectorAll(".density-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = !document.body.classList.contains("density-compact");
      apply(next);
      try { localStorage.setItem(KEY, next ? "1" : "0"); } catch (e) {}
    });
  });
})();


/* ============================================================
   Giscus theme bridge — sync our theme toggle with the giscus
   comment widget (blog posts). Uses giscus.sendMessage to set
   its theme without reloading.
   ============================================================ */
(function () {
  function giscusFrame() {
    return document.querySelector('iframe.giscus-frame');
  }
  function notifyGiscus(theme) {
    var frame = giscusFrame();
    if (!frame || !frame.contentWindow) return;
    var giscusTheme = theme === 'dark' ? 'dark' : theme === 'light' ? 'light' : 'preferred_color_scheme';
    frame.contentWindow.postMessage({ giscus: { setConfig: { theme: giscusTheme } } }, 'https://giscus.app');
  }
  function currentTheme() {
    var t = document.documentElement.getAttribute('data-theme');
    if (t) return t;
    // follow system
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  // Notify on load (once giscus iframe is ready)
  function onLoad() {
    var frame = giscusFrame();
    if (frame) {
      notifyGiscus(currentTheme());
    } else {
      // giscus loads async; retry a few times
      var tries = 0;
      var iv = setInterval(function () {
        tries++;
        if (giscusFrame()) { notifyGiscus(currentTheme()); clearInterval(iv); }
        else if (tries > 20) clearInterval(iv);
      }, 500);
    }
  }

  // Re-notify when theme toggle button is clicked (listen after our toggle applies)
  var observer = new MutationObserver(function () {
    notifyGiscus(currentTheme());
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onLoad);
  } else {
    onLoad();
  }
})();
