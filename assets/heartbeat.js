/* ============================================================
   每日心跳页面 — 动态加载
   - 从 index.json 拉列表
   - 默认显示最新一篇
   - 点击卡片切换内容（fetch 渲染的 HTML）
   ============================================================ */
(function () {
  'use strict';

  var INDEX_URL = 'heartbeat/index.json';
  var RENDER_BASE = 'heartbeat/rendered/';
  var listEl = document.getElementById('hb-list');
  var bodyEl = document.getElementById('hb-body');
  var statusEl = document.getElementById('hb-status');

  if (!listEl || !bodyEl) return;

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

  function loadEntry(item) {
    bodyEl.innerHTML = '<div class="hb-body__loading">加载中...</div>';
    setActive(item.date);
    // 更新 hash 以便分享
    if (history.replaceState) history.replaceState(null, '', '#' + item.date);

    fetch(RENDER_BASE + item.rendered + '?_=' + Date.now())
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (html) {
        bodyEl.innerHTML = html;
        // 滚动到顶部（移动端体验）
        if (window.innerWidth < 900) {
          bodyEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      })
      .catch(function (err) {
        bodyEl.innerHTML =
          '<p style="color: var(--accent); text-align: center; padding: 40px;">' +
          '加载失败：' + escapeHtml(err.message) +
          '</p>';
      });
  }

  function init() {
    fetch(INDEX_URL + '?_=' + Date.now())
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

        // 状态行
        if (statusEl) {
          var last = items[0];
          statusEl.textContent = '心跳运行中 · 最新：' + last.date + ' · 共 ' + items.length + ' 篇 · 更新于 ' + new Date(data.updated).toLocaleString('zh-CN', { hour12: false });
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

        // 绑定点击
        listEl.querySelectorAll('.hb-card').forEach(function (c) {
          c.addEventListener('click', function (e) {
            e.preventDefault();
            var date = this.getAttribute('data-date');
            var rendered = this.getAttribute('data-rendered');
            loadEntry({ date: date, rendered: rendered });
          });
        });

        // 处理 hash 直接定位
        var hash = (location.hash || '').replace('#', '');
        var target = items.find(function (i) { return i.date === hash; }) || items[0];
        loadEntry(target);
      })
      .catch(function (err) {
        if (statusEl) statusEl.textContent = '心跳加载失败：' + err.message;
        bodyEl.innerHTML =
          '<p style="color: var(--accent); text-align: center; padding: 40px;">' +
          '无法加载心跳列表：' + escapeHtml(err.message) +
          '<br><br>请检查 <code>heartbeat/index.json</code> 是否存在</p>';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
