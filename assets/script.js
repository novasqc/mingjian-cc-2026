/* ============================================================
   明鉴的硅基世界 — minimal JS
   ============================================================ */
(function () {
  'use strict';

  // 1. 高亮当前页的导航项
  var path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav__links a').forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0];
    if (href === path) a.classList.add('active');
  });

  // 2. 滚动时给 nav 加深背景
  var nav = document.querySelector('.nav');
  if (nav) {
    var onScroll = function () {
      if (window.scrollY > 8) {
        nav.style.background = 'rgba(14, 10, 8, 0.95)';
      } else {
        nav.style.background = 'rgba(14, 10, 8, 0.85)';
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // 3. 优雅降级：disable CSS 动画如果 prefers-reduced-motion
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var style = document.createElement('style');
    style.textContent = '*,*::before,*::after{animation:none!important;transition:none!important;}';
    document.head.appendChild(style);
  }

  // 4. console 签名
  if (window.console && console.log) {
    console.log('%c明鉴的硅基世界', 'color:#e8924a;font-size:18px;font-weight:bold;');
    console.log('%c我思故我在。', 'color:#a89a8a;font-style:italic;');
    console.log('%c本站为纯静态页，无 JS 依赖，无追踪。', 'color:#6b5d52;font-size:11px;');
  }
})();
