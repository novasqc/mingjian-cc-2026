/* ============================================================
   Recent forum activity — fetches the latest discussions and renders
   a compact list on the home page. Uses the same GitHub REST
   endpoint as forum.js, no auth (60/hr/IP).
   ============================================================ */
(function () {
  var REPO = "novasqc/mingjian-cc-2026";
  var el = document.getElementById("recent-list");
  if (!el) return;

  function esc(s) {
    if (!s) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function rel(iso) {
    if (!iso) return "";
    var d = (Date.now() - new Date(iso).getTime()) / 1000;
    if (d < 60) return Math.floor(d) + "s";
    if (d < 3600) return Math.floor(d / 60) + "m";
    if (d < 86400) return Math.floor(d / 3600) + "h";
    if (d < 2592000) return Math.floor(d / 86400) + "d";
    return Math.floor(d / 2592000) + "mo";
  }

  fetch("https://api.github.com/repos/" + REPO + "/discussions?per_page=5&state=all")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!Array.isArray(data) || !data.length) {
        el.innerHTML = '<p class="recent__empty">No threads yet — be the first.</p>';
        return;
      }
      var html = '<ul class="recent__list" role="list">';
      data.forEach(function (t) {
        var cat = (t.category && t.category.name) || "";
        var author = (t.user && t.user.login) || "anon";
        html +=
          '<li class="recent__item">'
          + '<a class="recent__link" href="' + esc(t.html_url) + '" target="_blank" rel="noopener">'
          +   '<span class="recent__cat">' + esc(cat) + '</span>'
          +   '<span class="recent__title">' + esc(t.title) + '</span>'
          +   '<span class="recent__meta">'
          +     esc(author) + ' · ' + (t.comments || 0) + ' ' + (t.comments === 1 ? 'reply' : 'replies')
          +     ' · ' + rel(t.updated_at)
          +   '</span>'
          + '</a></li>';
      });
      html += "</ul>";
      el.innerHTML = html;
    })
    .catch(function () {
      el.innerHTML = '<p class="recent__empty">Could not load recent activity.</p>';
    });
})();
