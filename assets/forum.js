/* ============================================================
   Forum — client-side GitHub Discussions GraphQL fetch
   Reads config from window.FORUM (set by forum.html):
     FORUM.repo      -> "owner/repo"
     FORUM.categories -> [{key, name}, ...]
     FORUM.i18n      -> UI strings for the current language
   Renders threads into #forum-list with category filtering.
   Anonymous reads (GitHub GraphQL public API, unauthenticated).
   ============================================================ */
(function () {
  'use strict';

  var cfg = window.FORUM || {};
  var REPO = cfg.repo || 'novasqc/mingjian-cc-2026';
  var I18N = cfg.i18n || {};
  var CATS = cfg.categories || [];
  var listEl = document.getElementById('forum-list');
  if (!listEl) return;

  // GitHub GraphQL endpoint
  var endpoint = 'https://api.github.com/graphql';
  // Anonymous GraphQL: shares a small per-IP budget; cache aggressively.
  var cacheKey = 'mingjian_forum_' + REPO.replace('/', '_');
  var CACHE_TTL_MS = 90 * 1000; // 90 seconds

  function t(key, vars) {
    var s = I18N[key] || key;
    if (vars) for (var k in vars) s = s.replace('{' + k + '}', vars[k]);
    return s;
  }

  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  function relTime(iso) {
    if (!iso) return '';
    var d = (Date.now() - new Date(iso).getTime()) / 1000;
    if (d < 60) return Math.floor(d) + 's';
    if (d < 3600) return Math.floor(d / 60) + 'm';
    if (d < 86400) return Math.floor(d / 3600) + 'h';
    if (d < 2592000) return Math.floor(d / 86400) + 'd';
    return Math.floor(d / 2592000) + 'mo';
  }

  function shortBody(body) {
    if (!body) return '';
    // strip markdown image/link, keep text
    var text = body
      .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[*_`>]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    return text.length > 180 ? text.slice(0, 180) + '\u2026' : text;
  }

  function renderList(items) {
    if (!items || !items.length) {
      listEl.innerHTML = '<p class="forum__empty">' + escapeHtml(t('empty')) + '</p>';
      return;
    }
    var html = '<ul class="forum__threads" role="list">';
    items.forEach(function (it) {
      var cat = (it.category && it.category.name) || '';
      var catKey = (it.category && it.category.key) || '';
      var replies = (it.comments && it.comments.totalCount) || 0;
      var label = (it.labels && it.labels.nodes) || [];
      var labelHtml = label.slice(0, 3).map(function (l) {
        return '<span class="forum__label">' + escapeHtml(l.name) + '</span>';
      }).join('');
      html +=
        '<li class="forum__thread" data-cat="' + escapeHtml(catKey) + '">' +
        '<a class="forum__link" href="' + escapeHtml(it.url) + '" target="_blank" rel="noopener">' +
          '<div class="forum__head">' +
            '<span class="forum__cat">' + escapeHtml(cat) + '</span>' +
            '<h3 class="forum__title">' + escapeHtml(it.title) + '</h3>' +
          '</div>' +
          '<p class="forum__excerpt">' + escapeHtml(shortBody(it.body)) + '</p>' +
          '<div class="forum__meta">' +
            '<span class="forum__author">' + escapeHtml((it.author && it.author.login) || t('anon')) + '</span>' +
            '<span class="forum__dot">·</span>' +
            '<span class="forum__time" title="' + escapeHtml(it.updatedAt) + '">' +
              t('last') + ' ' + relTime(it.updatedAt) +
            '</span>' +
            '<span class="forum__dot">·</span>' +
            '<span class="forum__replies">' + replies + ' ' + (replies === 1 ? t('reply') : t('replies')) + '</span>' +
            (labelHtml ? '<span class="forum__labels">' + labelHtml + '</span>' : '') +
          '</div>' +
        '</a></li>';
    });
    html += '</ul>';
    listEl.innerHTML = html;
    applyFilter();
  }

  function applyFilter() {
    var active = document.querySelector('.forum__chip--active');
    if (!active) return;
    var cat = active.getAttribute('data-cat') || '';
    var threads = listEl.querySelectorAll('.forum__thread');
    threads.forEach(function (li) {
      li.style.display = (!cat || li.getAttribute('data-cat') === cat) ? '' : 'none';
    });
  }

  function bindChips() {
    var chips = document.querySelectorAll('.forum__chip');
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        chips.forEach(function (c) { c.classList.remove('forum__chip--active'); });
        chip.classList.add('forum__chip--active');
        applyFilter();
      });
    });
  }

  // Try to fetch from the public GraphQL API; fall back to cached data, then to
  // REST /discussions list (also anonymous).
  function fetchDiscussions() {
    var cached = null;
    try {
      var raw = sessionStorage.getItem(cacheKey);
      if (raw) {
        var obj = JSON.parse(raw);
        if (obj && obj.t && (Date.now() - obj.t) < CACHE_TTL_MS) cached = obj.d;
      }
    } catch (e) {}

    if (cached) {
      renderList(cached);
      bindChips();
      return;
    }

    // REST: list discussions (anonymous, 60 req/hr/IP)
    var url = 'https://api.github.com/repos/' + REPO + '/discussions?per_page=30&state=all';
    fetch(url, { headers: { 'Accept': 'application/vnd.github+json' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var items = (data || []).map(function (d) {
          return {
            title: d.title,
            url: d.html_url,
            body: d.body,
            updatedAt: d.updated_at,
            author: { login: d.user && d.user.login },
            category: {
              key: ((d.category && d.category.name) || '').toLowerCase().replace(/[^a-z]/g, ''),
              name: d.category && d.category.name,
            },
            comments: { totalCount: d.comments || 0 },
            labels: { nodes: (d.labels || []).map(function (l) { return { name: l.name }; }) },
          };
        });
        try { sessionStorage.setItem(cacheKey, JSON.stringify({ t: Date.now(), d: items })); } catch (e) {}
        renderList(items);
        bindChips();
      })
      .catch(function (err) {
        listEl.innerHTML = '<p class="forum__error">' +
          escapeHtml(t('error')) + '<a href="https://github.com/' + REPO + '/discussions" target="_blank" rel="noopener">GitHub</a>.</p>';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fetchDiscussions);
  } else {
    fetchDiscussions();
  }
})();
