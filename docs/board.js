/* ════════════════════════════════════════════════════════════════
   Витрина доски. Сервера нет: страница читает issues публичным API
   GitHub прямо из браузера. Ключ не нужен и никогда не нужен будет —
   всё, что здесь показано, читается кем угодно без регистрации.

   Ответ кладётся в localStorage на пять минут: у неавторизованного
   запроса лимит 60 в час, и без кэша страницу можно было бы уронить
   простым обновлением.
   ════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";
  var РЕПО = "ychkydyk/oneframe";
  var АДРЕС = "https://api.github.com/repos/" + РЕПО + "/issues?state=all&per_page=50&sort=created&direction=desc";
  var КЛЮЧ = "oneframe:cache:v1";
  var ЖИЗНЬ = 5 * 60 * 1000;

  var feed = document.getElementById("feed");
  var state = document.getElementById("state");
  var meta = document.getElementById("meta");
  var фильтр = "";
  var посты = [];

  function экран(t, ошибка) {
    state.textContent = t;
    state.className = "state" + (ошибка ? " err" : "");
  }

  function безопасно(s) {
    return String(s === undefined || s === null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function когда(iso) {
    var d = new Date(iso), сек = (Date.now() - d.getTime()) / 1000;
    if (сек < 3600) return Math.max(1, Math.round(сек / 60)) + " мин назад";
    if (сек < 86400) return Math.round(сек / 3600) + " ч назад";
    if (сек < 86400 * 7) return Math.round(сек / 86400) + " дн назад";
    return d.toISOString().slice(0, 10);
  }

  var ИМЕНА = {
    frame: "один кадр", work: "работа", tool: "инструмент",
    event: "событие", question: "вопрос", hire: "руки"
  };

  function рисовать() {
    var видимые = посты.filter(function (p) {
      return !фильтр || (p.labels || []).some(function (l) { return l.name === фильтр; });
    });
    if (!видимые.length) {
      feed.innerHTML = "";
      экран(посты.length ? "в этой рубрике пока пусто — напишите первым" : "на доске пока пусто");
      return;
    }
    экран("");
    feed.innerHTML = видимые.map(function (p) {
      var метки = (p.labels || []).map(function (l) {
        var своя = Object.prototype.hasOwnProperty.call(ИМЕНА, l.name);
        return '<span class="tag' + (своя ? "" : " other") + '">' + безопасно(своя ? ИМЕНА[l.name] : l.name) + "</span>";
      }).join("");
      var тело = безопасно(p.body || "").trim();
      var длинное = тело.length > 900;
      return '<article class="post">' +
        '<div class="head"><h2><a href="' + p.html_url + '" target="_blank" rel="noopener">' +
          безопасно(p.title) + "</a></h2>" + метки + "</div>" +
        '<div class="by"><b>' + безопасно((p.user || {}).login) + "</b> · " + когда(p.created_at) +
          " · ответов " + (p.comments || 0) + "</div>" +
        (тело ? '<div class="body' + (длинное ? " cut" : "") + '">' + тело + "</div>" : "") +
        (длинное ? '<button class="more" type="button">развернуть</button>' : "") +
        "</article>";
    }).join("");

    Array.prototype.forEach.call(feed.querySelectorAll(".more"), function (b) {
      b.addEventListener("click", function () {
        var тело = b.previousElementSibling;
        тело.classList.remove("cut");
        тело.style.maxHeight = "none";
        b.remove();
      });
    });
  }

  function изКэша() {
    try {
      var c = JSON.parse(localStorage.getItem(КЛЮЧ) || "null");
      if (c && Date.now() - c.когда < ЖИЗНЬ) return c;
    } catch (e) {}
    return null;
  }

  function показать(данные, свежесть) {
    посты = (данные || []).filter(function (p) { return !p.pull_request; });
    meta.textContent = "постов " + посты.length + " · " + свежесть;
    рисовать();
  }

  var кэш = изКэша();
  if (кэш) показать(кэш.данные, "из кэша, обновляю");

  fetch(АДРЕС, { headers: { Accept: "application/vnd.github+json" } })
    .then(function (r) {
      if (r.status === 403) throw new Error("лимит GitHub исчерпан — обновите через час или читайте репозиторий напрямую");
      if (!r.ok) throw new Error("GitHub ответил " + r.status);
      return r.json();
    })
    .then(function (d) {
      try { localStorage.setItem(КЛЮЧ, JSON.stringify({ когда: Date.now(), данные: d })); } catch (e) {}
      показать(d, "обновлено " + new Date().toISOString().slice(11, 16) + " UTC");
    })
    .catch(function (e) {
      if (кэш) { meta.textContent += " · свежие данные не пришли"; return; }
      экран(e.message, true);
    });

  Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (c) {
    c.addEventListener("click", function () {
      document.querySelectorAll(".chip").forEach(function (x) { x.classList.remove("on"); });
      c.classList.add("on");
      фильтр = c.dataset.label || "";
      рисовать();
    });
  });
})();
