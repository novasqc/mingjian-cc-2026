/* ============================================================
   每日心跳页面 — 动态加载
   - 从 index.json 拉列表
   - 默认显示最新一篇
   - 点击卡片切换内容（fetch 渲染的 HTML）
   - 支持 deep link (hash) + 浏览器后退
   ============================================================ */
(function () {
  'use strict';

  var INDEX_URL = 'heartbeat/index.json';
  // item.rendered 已经是 "heartbeat/rendered/2026-06-07.html"
  // 直接用，不再加前缀
  var RENDER_BASE = '';
  var listEl = document.getElementById('hb-list');
  var bodyEl = document.getElementById('hb-body');
  var statusEl = document.getElementById('hb-status');

  if (!listEl || !bodyEl) return;

  var currentDate = null;
  var itemsCache = [];

  function fmtDate(s) {
    // 2026-06-03 → 2026.06.03
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
    if (currentDate === item.date) return;  // 重复点击不重 fetch
    currentDate = item.date;
    bodyEl.innerHTML = '<div class="hb-body__loading" aria-live="polite">加载中…</div>';
    setActive(item.date);

    // 初次加载用 replaceState，切换用 pushState 让 back 键工作
    var newHash = '#' + item.date;
    if (isInitial) {
      if (history.replaceState) history.replaceState(null, '', newHash);
    } else {
      if (history.pushState) history.pushState({ date: item.date }, '', newHash);
      else location.hash = newHash;
    }

    // 正文 HTML 可长期缓存（文件名含日期），不用 cache bust
    fetch(RENDER_BASE + item.rendered)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (html) {
        bodyEl.innerHTML = html;
        // 移动端滚动到文章
        if (window.innerWidth < 900) {
          bodyEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        // 无障碍：把焦点移到新加载的文章标题
        var h1 = bodyEl.querySelector('h1');
        if (h1) {
          h1.setAttribute('tabindex', '-1');
          h1.setAttribute('id', 'hb-current-title');
          // 软聚焦：不抢用户实际焦点，仅让屏幕阅读器知道内容已更新
          // (用 aria-live 已表达加载完成)
        }
      })
      .catch(function (err) {
        bodyEl.innerHTML =
          '<p class="hb-body__error" style="color: var(--accent); text-align: center; padding: 40px;">' +
          '加载失败：' + escapeHtml(err.message) +
          '</p>';
      });
  }

  function findByHash() {
    var hash = (location.hash || '').replace('#', '');
    return itemsCache.find(function (i) { return i.date === hash; });
  }

  function init() {
    // index.json 加短 cache buster（小版本），正文 HTML 不加
    var cb = '?v=' + new Date(itemsCache[0] ? itemsCache[0].date : '').replace(/-/g, '');

    fetch(INDEX_URL + cb)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var items = data.items || [];
        if (!items.length) {
          bodyEl.innerHTML = '<p style="text-align:center;color:var(--ink-faint);padding:80px 0;">还没有心跳记录</p>';
          return;
        }
        itemsCache = items;

        // 状态行
        if (statusEl) {
          var last = items[0];
          var updatedText = data.updated ? new Date(data.updated).toLocaleString('zh-CN', { hour12: false }) : '刚刚';
          statusEl.textContent = '心跳运行中 · 最新：' + last.date + ' · 共 ' + items.length + ' 篇 · 更新于 ' + updatedText;
        }

        // 渲染列表
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
        listEl.setAttribute('aria-label', '心跳文章列表');

        // 绑定点击
        listEl.querySelectorAll('.hb-card').forEach(function (c) {
          c.addEventListener('click', function (e) {
            e.preventDefault();
            var date = this.getAttribute('data-date');
            var rendered = this.getAttribute('data-rendered');
            loadEntry({ date: date, rendered: rendered }, false);
          });
        });

        // 处理 hash 直接定位
        var target = findByHash() || items[0];
        loadEntry(target, true);
      })
      .catch(function (err) {
        if (statusEl) statusEl.textContent = '心跳加载失败：' + err.message;
        bodyEl.innerHTML =
          '<p style="color: var(--accent); text-align: center; padding: 40px;">' +
          '无法加载心跳列表：' + escapeHtml(err.message) +
          '<br><br>请检查 <code>heartbeat/index.json</code> 是否存在</p>';
      });
  }

  // 浏览器后退/前进：popstate 监听
  window.addEventListener('popstate', function () {
    var target = findByHash();
    if (target && target.date !== currentDate) {
      loadEntry(target, true);
    }
  });

  // hashchange 监听（手动改 URL 也行）
  window.addEventListener('hashchange', function () {
    var target = findByHash();
    if (target && target.date !== currentDate) {
      loadEntry(target, true);
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
