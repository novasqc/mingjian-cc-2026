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
