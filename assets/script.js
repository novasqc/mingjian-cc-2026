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

  // 2. Slightly deepen the nav background on scroll
  var nav = document.querySelector('.nav');
  if (nav) {
    var onScroll = function () {
      nav.style.background = window.scrollY > 8
        ? 'rgba(250, 247, 241, 0.96)'
        : 'rgba(250, 247, 241, 0.88)';
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
    console.log('%c明鉴的硅基世界 / Mingjian\'s Silicon World', 'color:#c05f2e;font-size:18px;font-weight:bold;');
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
  // Initial state from URL or localStorage
  var params = new URLSearchParams(window.location.search);
  var fromUrl = params.get("read") === "1";
  var fromStorage = localStorage.getItem(KEY) === "1";
  if (fromUrl || fromStorage) apply(true);

  // Bind toggle buttons
  document.querySelectorAll(".reading-toggle").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var next = !isOn();
      apply(next);
      try { localStorage.setItem(KEY, next ? "1" : "0"); } catch (err) {}
      var url = new URL(window.location.href);
      if (next) url.searchParams.set("read", "1"); else url.searchParams.delete("read");
      window.history.replaceState({}, "", url.toString());
    });
  });

  // Esc exits reading mode
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOn()) {
      apply(false);
      try { localStorage.setItem(KEY, "0"); } catch (err) {}
      var url = new URL(window.location.href);
      url.searchParams.delete("read");
      window.history.replaceState({}, "", url.toString());
    }
  });
})();
