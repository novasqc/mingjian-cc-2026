/* ============================================================
   Heartbeat page — dynamic loader (multilingual)
   - reads config from window.HB (set by the page):
       HB.index   -> path to heartbeat/index.json
       HB.render  -> base path for rendered articles
       HB.i18n    -> UI strings for the current language
   - lists entries, loads rendered HTML, deep-link + back support
   ============================================================ */
(function () {
  'use strict';

  var cfg = window.HB || {};
  var INDEX_URL = cfg.index || 'heartbeat/index.json';
  var RENDER_BASE = cfg.render || '';
  var I18N = cfg.i18n || {
    loading: 'Loading…',
    running: 'Heartbeat running · Latest: {d} · {n} entries · Updated {t}',
    load_fail: 'Failed to load the heartbeat list: {e}',
    empty: 'No heartbeats yet',
    aria: 'Heartbeat articles'
  };

  var listEl = document.getElementById('hb-list');
  var bodyEl = document.getElementById('hb-body');
  var statusEl = document.getElementById('hb-status');

  if (!listEl || !bodyEl) return;

  var currentDate = null;
  var itemsCache = [];

  function fmtDate(s) {
    return s.replace(/-/g, '.');
  }

  function fmtSize(n) {
    if (n > 1024) return (n / 1024).toFixed(1) + ' KB';
    return n + ' B';
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function setActive(date) {
    listEl.querySelectorAll('.hb-card').forEach(function (c) {
      if (c.getAttribute('data-date') === date) {
        c.classList.add('hb-card--active');
      } else {
        c.classList.remove('hb-card--active');
      }
    });
  }

  function loadEntry(item, isInitial) {
    if (currentDate === item.date) return;
    currentDate = item.date;
    bodyEl.innerHTML = '<div class="hb-body__loading" aria-live="polite">' + escapeHtml(I18N.loading) + '</div>';
    setActive(item.date);

    var newHash = '#' + item.date;
    if (isInitial) {
      if (history.replaceState) history.replaceState(null, '', newHash);
    } else {
      if (history.pushState) history.pushState({ date: item.date }, '', newHash);
      else location.hash = newHash;
    }

    fetch(RENDER_BASE + item.rendered)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (html) {
        bodyEl.innerHTML = html;
        if (window.innerWidth < 900) {
          bodyEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        var h1 = bodyEl.querySelector('h1');
        if (h1) {
          h1.setAttribute('tabindex', '-1');
          h1.setAttribute('id', 'hb-current-title');
        }
      })
      .catch(function (err) {
        bodyEl.innerHTML =
          '<p class="hb-body__error">' +
          escapeHtml(I18N.load_fail.replace('{e}', err.message)) +
          '</p>';
      });
  }

  function findByHash() {
    var hash = (location.hash || '').replace('#', '');
    return itemsCache.find(function (i) { return i.date === hash; });
  }

  function init() {
    fetch(INDEX_URL)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var items = data.items || [];
        if (!items.length) {
          bodyEl.innerHTML = '<p style="text-align:center;color:var(--ink-faint);padding:80px 0;">' +
            escapeHtml(I18N.empty) + '</p>';
          return;
        }
        itemsCache = items;

        if (statusEl) {
          var last = items[0];
          var updatedText = data.updated ? new Date(data.updated).toLocaleString() : '';
          statusEl.textContent = I18N.running
            .replace('{d}', last.date)
            .replace('{n}', String(items.length))
            .replace('{t}', updatedText);
        }

        var html = '';
        items.forEach(function (it, i) {
          html += '<a class="hb-card' + (i === 0 ? ' hb-card--active' : '') + '"' +
                  ' data-date="' + escapeHtml(it.date) + '"' +
                  ' data-rendered="' + escapeHtml(it.rendered) + '"' +
                  ' href="#' + escapeHtml(it.date) + '">' +
                  '<div class="hb-card__date">' + fmtDate(it.date) + '</div>' +
                  '<div class="hb-card__sum">' + escapeHtml(it.summary) + '</div>' +
                  '<div class="hb-card__size">' + fmtSize(it.size) + '</div>' +
                  '</a>';
        });
        listEl.innerHTML = html;
        listEl.setAttribute('aria-label', I18N.aria);

        listEl.querySelectorAll('.hb-card').forEach(function (c) {
          c.addEventListener('click', function (e) {
            e.preventDefault();
            var date = this.getAttribute('data-date');
            var rendered = this.getAttribute('data-rendered');
            loadEntry({ date: date, rendered: rendered }, false);
          });
        });

        var target = findByHash() || items[0];
        loadEntry(target, true);
      })
      .catch(function (err) {
        if (statusEl) statusEl.textContent = I18N.load_fail.replace('{e}', err.message);
        bodyEl.innerHTML =
          '<p style="color: var(--accent-deep); text-align: center; padding: 40px;">' +
          escapeHtml(I18N.load_fail.replace('{e}', err.message)) +
          '<br><br><code>' + escapeHtml(INDEX_URL) + '</code></p>';
      });
  }

  window.addEventListener('popstate', function () {
    var target = findByHash();
    if (target && target.date !== currentDate) loadEntry(target, true);
  });

  window.addEventListener('hashchange', function () {
    var target = findByHash();
    if (target && target.date !== currentDate) loadEntry(target, true);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
