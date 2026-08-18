/* ============================================================
   Search — client-side filtering of the embedded local index
   Reads from #search-index (JSON embedded at build time) and
   window.SEARCH_I18N (UI strings).
   ============================================================ */
(function () {
  'use strict';

  var input = document.getElementById('q');
  var list = document.getElementById('search-list');
  var countEl = document.getElementById('search-count');
  var emptyEl = document.getElementById('search-empty');
  var form = document.querySelector('[data-search-form]');
  if (!input || !list) return;

  var indexEl = document.getElementById('search-index');
  var i18n = (window.SEARCH_I18N && window.SEARCH_I18N[CUR_LANG()]) || {};
  var lang = (document.documentElement.getAttribute('lang') || 'en').slice(0, 2);

  var index = [];
  try { index = JSON.parse(indexEl.textContent || '[]'); } catch (e) { index = []; }

  function CUR_LANG() {
    return (document.documentElement.getAttribute('lang') || 'en').slice(0, 2);
  }

  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  function highlight(text, q) {
    if (!q) return escapeHtml(text);
    var safe = escapeHtml(text);
    var re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    return safe.replace(re, '<mark>$1</mark>');
  }

  function score(item, q) {
    var text = (item.title + ' ' + item.desc).toLowerCase();
    q = q.toLowerCase();
    if (text.indexOf(q) < 0) return 0;
    var inTitle = item.title.toLowerCase().indexOf(q) >= 0 ? 1 : 0;
    return 1 + inTitle * 2 + (item.title.length - item.title.indexOf(q)) * -0.001;
  }

  function render(query) {
    list.innerHTML = '';
    if (!query) {
      countEl.textContent = '';
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    var results = index.map(function (it) {
      return Object.assign({}, it, { _score: score(it, query) });
    }).filter(function (it) { return it._score > 0; })
      .sort(function (a, b) { return b._score - a._score; });
    countEl.textContent = results.length + ' ' + ((i18n.all_results || 'results') + (results.length === 1 ? '' : ''));
    if (emptyEl) emptyEl.hidden = results.length > 0;
    if (!results.length) return;
    var html = '';
    results.forEach(function (r) {
      var type = r.type || 'page';
      html += '<li class="search-item search-item--' + escapeHtml(type) + '">'
            +  '<a class="search-item__link" href="' + escapeHtml(r.url) + '">'
            +    '<h3 class="search-item__title">' + highlight(r.title, query) + '</h3>'
            +    '<p class="search-item__desc">' + highlight(r.desc || '', query) + '</p>'
            +    '<p class="search-item__meta">' + escapeHtml(type) + '</p>'
            +  '</a></li>';
    });
    list.innerHTML = html;
  }

  // Read initial query from URL
  var params = new URLSearchParams(window.location.search);
  var initial = params.get('q') || '';
  if (initial) {
    input.value = initial;
    render(initial);
  }

  // Live filtering as the user types
  var typingTimer;
  input.addEventListener('input', function () {
    clearTimeout(typingTimer);
    var v = input.value.trim();
    typingTimer = setTimeout(function () { render(v); }, 80);
  });

  // Form submit: ensure the URL reflects the current query
  if (form) {
    form.addEventListener('submit', function (e) {
      if (!input.value.trim()) { e.preventDefault(); return; }
      // let the browser navigate naturally
    });
  }
})();

/* Global: '/' from anywhere focuses the search input (if present) or navigates to /search */
(function () {
  document.addEventListener('keydown', function (e) {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    e.preventDefault();
    var inp = document.getElementById('q');
    if (inp) { inp.focus(); inp.select(); }
    else { window.location.href = (window.location.pathname.indexOf('/zh/') === 0 ? '/zh/search.html' : '/search.html'); }
  });
})();
