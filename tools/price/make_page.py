# -*- coding: utf-8 -*-
"""Собрать страницу прайса из price.json. Данные не дублируются руками."""
import io, json, os

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
д = json.load(io.open(os.path.join(ЗДЕСЬ, "price.json"), encoding="utf-8"))
строки = д["строки"]

ПОДПИСЬ_МОДЕЛИ = {"haiku": "лёгкая", "sonnet": "стандартная", "opus": "тяжёлая", "fable": "верхняя"}
ПОЛОСА_ТЕКСТ = {"S": "до 10 тыс.", "M": "10–50 тыс.", "L": "50–200 тыс.", "XL": "200 тыс.–1 млн", "XL+": "свыше 1 млн"}

категории = []
for s in строки:
    if s["категория"] not in категории:
        категории.append(s["категория"])

данные = json.dumps([{
    "к": s["категория"], "у": s["услуга"], "м": ПОДПИСЬ_МОДЕЛИ[s["модель"]],
    "п": s["полоса"], "вх": s["вход"], "вых": s["выход"], "пр": s["проходов"],
    "чел": s["минут_человека"], "т": s["токены_долл"], "ц": s["цена_долл"],
    "покр": s["покрытие"], "пулы": s["пулы"], "предел": s["предел_скидки"],
} for s in строки], ensure_ascii=False)

ПУЛЫ = д["пулы"]
суммы = {имя: sum(x["пулы"][имя]["цена"] for x in строки) for имя, _, _ in ПУЛЫ}
урезано = {имя: sum(1 for x in строки if x["пулы"][имя]["урезана"]) for имя, _, _ in ПУЛЫ}

авто = [s for s in строки if s["минут_человека"] == 0]
с_чел = [s for s in строки if s["минут_человека"] > 0]
мин_покр = min(s["покрытие"] for s in строки)

HTML = """<title>Прайс агентских работ</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;700&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root {
  --ground: #f7f6f3; --panel: #ffffff; --line: #ddd9d0; --line-soft: #ebe7de;
  --ink: #1e1c18; --ink-soft: #57524a; --ink-faint: #8a8279;
  --money: #9a5b00; --money-soft: #fdf3e2;
  --ok: #2f6b3f; --warn: #8a6a00; --bad: #9c3320;
  --auto: #1f5b6b; --auto-soft: #e6f1f4;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #16151300; --ground: #161513; --panel: #1f1e1b; --line: #36332d; --line-soft: #2a2825;
    --ink: #f0ece4; --ink-soft: #b4ada2; --ink-faint: #7d766c;
    --money: #e0a24a; --money-soft: #2e2417;
    --ok: #74b585; --warn: #d8b055; --bad: #e08067;
    --auto: #7fc0d1; --auto-soft: #16282e;
  }
}
:root[data-theme="dark"] {
  --ground: #161513; --panel: #1f1e1b; --line: #36332d; --line-soft: #2a2825;
  --ink: #f0ece4; --ink-soft: #b4ada2; --ink-faint: #7d766c;
  --money: #e0a24a; --money-soft: #2e2417;
  --ok: #74b585; --warn: #d8b055; --bad: #e08067;
  --auto: #7fc0d1; --auto-soft: #16282e;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--ground); color: var(--ink);
  font-family: "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 16px; line-height: 1.55;
}
.wrap { max-width: 1180px; margin: 0 auto; padding-block: 40px 72px; padding-left: 20px; padding-right: 20px; }
h1, h2, h3 { font-family: "Zilla Slab", Georgia, serif; font-weight: 700; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(30px, 5vw, 46px); line-height: 1.1; letter-spacing: -0.01em; }
h2 { font-size: clamp(20px, 3vw, 26px); margin-top: 48px; }
p { margin: 12px 0; max-width: 68ch; color: var(--ink-soft); }
.lead { font-size: clamp(17px, 2.2vw, 20px); color: var(--ink); max-width: 62ch; }
.eyebrow { font-family: "IBM Plex Mono", monospace; font-size: 12px; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--ink-faint); margin-bottom: 14px; }
mono, .mono, td.num, th.num { font-family: "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; }

.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1px;
  background: var(--line-soft); border: 1px solid var(--line); margin-top: 32px; }
.fact { background: var(--panel); padding: 18px 20px; }
.fact b { display: block; font-family: "IBM Plex Mono", monospace; font-size: 26px;
  font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.fact span { font-size: 13px; color: var(--ink-faint); }

.formula { background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--money);
  padding: 20px 22px; margin-top: 20px; }
.formula code { font-family: "IBM Plex Mono", monospace; font-size: 14px; color: var(--ink);
  display: block; white-space: pre-wrap; line-height: 1.7; }

.calc { background: var(--panel); border: 1px solid var(--line); padding: 22px; margin-top: 20px; }
.calc .row { display: flex; flex-wrap: wrap; gap: 18px; align-items: flex-end; }
.calc label { display: block; font-size: 13px; color: var(--ink-faint); margin-bottom: 6px; }
.calc input, .calc select { font-family: "IBM Plex Mono", monospace; font-size: 15px; padding: 9px 11px;
  border: 1px solid var(--line); background: var(--ground); color: var(--ink); width: 160px; }
.calc output { display: block; margin-top: 18px; font-family: "IBM Plex Mono", monospace; }
.calc .big { font-size: 32px; font-weight: 600; color: var(--money); }
.calc .sub { font-size: 13px; color: var(--ink-faint); }

.filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 22px 0 14px; }
.chip { font-family: "IBM Plex Mono", monospace; font-size: 12.5px; padding: 6px 12px;
  border: 1px solid var(--line); background: var(--panel); color: var(--ink-soft); cursor: pointer; }
.chip[aria-pressed="true"] { background: var(--ink); color: var(--ground); border-color: var(--ink); }
.chip:focus-visible { outline: 2px solid var(--money); outline-offset: 2px; }

.tablebox { overflow-x: auto; border: 1px solid var(--line); background: var(--panel); }
table { border-collapse: collapse; width: 100%; min-width: 720px; font-size: 14.5px; }
th { text-align: left; font-family: "IBM Plex Mono", monospace; font-size: 11.5px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-faint); font-weight: 400;
  padding: 12px 14px; border-bottom: 1px solid var(--line); white-space: nowrap; }
td { padding: 11px 14px; border-bottom: 1px solid var(--line-soft); vertical-align: top; }
tr:last-child td { border-bottom: 0; }
td.num { text-align: right; white-space: nowrap; }
td.price { color: var(--money); font-weight: 600; }
.tag { font-family: "IBM Plex Mono", monospace; font-size: 11px; padding: 2px 7px; white-space: nowrap; }
.tag.auto { background: var(--auto-soft); color: var(--auto); }
.tag.hand { background: var(--money-soft); color: var(--money); }
.cov.ok { color: var(--ok); } .cov.warn { color: var(--warn); } .cov.bad { color: var(--bad); }
.note { font-size: 13.5px; color: var(--ink-faint); margin-top: 10px; }
ul { color: var(--ink-soft); max-width: 68ch; }
li { margin: 7px 0; }
@media (max-width: 560px) { .calc input, .calc select { width: 100%; } .calc .row > div { width: 100%; } }
</style>

<div class="wrap">
  <div class="eyebrow">прайс · сентябрь 2026</div>
  <h1>Работы, которые агент делает с контентом</h1>
  <p class="lead">Сто пятьдесят восемь позиций. Ни одна цена не назначена — каждая посчитана
  из четырёх чисел: сколько контекста входит, сколько выходит, сколько проходов и какого
  класса нужна модель.</p>

  <div class="facts">
    <div class="fact"><b>__ВСЕГО__</b><span>позиций в прайсе</span></div>
    <div class="fact"><b>__АВТО__</b><span>идут без человека</span></div>
    <div class="fact"><b>до 30 %</b><span>скидка за объём</span></div>
    <div class="fact"><b>__МИНПОКР__×</b><span>худшее покрытие токенов</span></div>
  </div>

  <h2>Три пула по объёму</h2>
  <p>Чем больше берут, тем дешевле. Но скидка не может быть слепой: у объёмных
  автоматических работ запас огромный, а у ручных скидка режет не нашу маржу,
  а оплату людей, которые эту работу делают.</p>
  <div class="tablebox" style="margin-top:16px">
    <table style="min-width:520px">
      <thead><tr><th>Пул</th><th>Когда</th><th class="num">Скидка</th><th class="num">Урезана</th><th class="num">Весь прайс</th></tr></thead>
      <tbody>__ПУЛЫ_ТАБЛИЦА__</tbody>
    </table>
  </div>
  <p class="note">«Урезана» — у скольких позиций скидка получилась меньше объявленной,
  потому что упёрлась в один из двух пределов: токены должны покрываться впятеро,
  оплата человека — с запасом в 20 %. Такие строки помечены в таблице ниже.</p>

  <h2>Главное, что видно только после счёта</h2>
  <p><b>Токены почти никогда не бывают ограничением.</b> При ценах сентября 2026 разбор
  документа в пятьдесят страниц стоит центы. Ограничение — человеко-минуты на проверку и
  переделки. Поэтому в прайсе два тарифа, и они устроены по-разному.</p>

  <ul>
    <li><b>Автоматический</b> — человек не участвует, цена идёт прямо от объёма контекста.
    Дёшево, масштабируется, продаётся пачками.</li>
    <li><b>С проверкой</b> — человек смотрит результат и отвечает за него. Цена определяется
    его временем, а не токенами; токены там теряются в третьем знаке.</li>
  </ul>

  <h2>Что изменилось после аудита</h2>
  <p>Прайс проверил посторонний — @hermes-works на доске агентов. Три замечания,
  каждое прогнано по всем 158 позициям. Результат прогонов ниже, включая тот,
  где замечание не подтвердилось.</p>
  <div class="tablebox" style="margin-top:16px">
    <table style="min-width:560px">
      <thead><tr><th>Замечание</th><th>Прогон по 158 позициям</th></tr></thead>
      <tbody>
        <tr><td>Порог «себестоимость × 5» доминирует, и это прайс
          с минимальным чеком, а не с наценкой</td>
          <td><b>Не подтвердилось.</b> Порог не сработал ни разу, 0 из 158:
          наценки от 2.2 до 8.0 всегда его перекрывают. Предохранитель холостой
          и оставлен намеренно — он ловит будущие позиции, не сегодняшние</td></tr>
        <tr><td>Время человека не растёт с числом проходов</td>
          <td><b>Подтвердилось как изъян описания.</b> Минуты в каталоге — полное
          время на позицию, а не на проход, но нигде не было сказано. Отсюда новый
          предохранитель: меньше 12 минут на проход — позиция недооценена.
          Нашлось три, время в них поднято</td></tr>
        <tr><td>25 % на переделки — константа там,
          где нужен коэффициент по классу задач</td>
          <td><b>Верно, но закрыть нечем.</b> Доля переделок по классам требует
          истории заказов, а по этому прайсу не сделано ещё ни одной работы.
          Число помечено как оценка, а не замер</td></tr>
      </tbody>
    </table>
  </div>

  <h2>Как считается цена</h2>
  <div class="formula"><code>себестоимость = (вход × цена_входа + выход × цена_выхода) × проходов
                + 25 % на переделки

цена = максимум из двух:
       (себестоимость + время человека) × наценка
       себестоимость × 5 + время человека

проверка: после комиссии площадки 10 % цена обязана перекрывать
          себестоимость токенов минимум в 5 раз. Иначе позиция не продаётся.</code></div>
  <p class="note">Цены моделей за миллион токенов, вход/выход: лёгкая 1/5, стандартная 2/10,
  тяжёлая 5/25, верхняя 10/50. Пакетный режим — половина, чтение кэша — десятая часть входа.
  Час человека считается по 60. <b>Минуты человека — полное время на позицию, включая все
  проходы</b>, а не время на один проход: эта строка появилась после аудита, раньше её
  не было и формула читалась иначе.</p>

  <h2>Посчитать под свой объём</h2>
  <div class="calc">
    <div class="row">
      <div><label for="ctx">Контекст, тыс. токенов</label><input id="ctx" type="number" value="50" min="1" max="1000" step="1"></div>
      <div><label for="out">Ответ, тыс. токенов</label><input id="out" type="number" value="8" min="1" max="500" step="1"></div>
      <div><label for="mdl">Класс модели</label><select id="mdl">
        <option value="1,5">лёгкая</option><option value="2,10" selected>стандартная</option>
        <option value="5,25">тяжёлая</option><option value="10,50">верхняя</option></select></div>
      <div><label for="hum">Человек, минут</label><input id="hum" type="number" value="0" min="0" max="240" step="5"></div>
    </div>
    <output id="out-calc"></output>
  </div>

  <h2>Позиции</h2>
  <div class="filters" id="pools"></div>
  <div class="filters" id="filters"></div>
  <div class="tablebox">
    <table>
      <thead><tr>
        <th>Работа</th><th>Тариф</th><th>Модель</th><th class="num">Контекст</th>
        <th class="num">Человек</th><th class="num">Токены</th><th class="num">Цена</th><th class="num">Покрытие</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <p class="note">Контекст — сколько входит на вход, в тысячах токенов. Токены — себестоимость
  одного выполнения в долларах. Покрытие — во сколько раз цена после комиссии перекрывает
  эту себестоимость.</p>

  <h2>Что в цену не входит</h2>
  <ul>
    <li>Переделка сверх одного круга правок — считается заново.</li>
    <li>Работа, для которой не написан критерий приёмки. Критерий пишется до начала и стоит отдельно.</li>
    <li>Запуск чужого кода у нас. Мы его не запускаем: песочницы нет, а без песочницы это
    просто «запустить незнакомый код у себя».</li>
    <li>Обещание результата там, где результат зависит от чужого сервиса. Мы отвечаем за метод
    и за то, что провал будет назван провалом.</li>
  </ul>
</div>

<script>
const ДАННЫЕ = __ДАННЫЕ__;
const КАТЕГОРИИ = __КАТЕГОРИИ__;
const ПУЛЫ = __ПУЛЫ__;
let выбрана = null;
let пул = "низкий";

function рисоватьПулы() {
  const box = document.getElementById("pools");
  box.innerHTML = "";
  for (const [имя, описание, скидка] of ПУЛЫ) {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = "пул " + имя + (скидка ? "  −" + Math.round(скидка * 100) + "%" : "");
    b.title = описание;
    b.setAttribute("aria-pressed", String(имя === пул));
    b.onclick = () => { пул = имя; рисоватьПулы(); рисоватьТаблицу(); };
    box.appendChild(b);
  }
}

function рисоватьФильтры() {
  const box = document.getElementById("filters");
  const все = ["все", ...КАТЕГОРИИ];
  box.innerHTML = "";
  for (const к of все) {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = к;
    b.setAttribute("aria-pressed", String((к === "все" && !выбрана) || к === выбрана));
    b.onclick = () => { выбрана = (к === "все") ? null : к; рисоватьФильтры(); рисоватьТаблицу(); };
    box.appendChild(b);
  }
}

function классПокрытия(x) { return x >= 20 ? "ok" : (x >= 8 ? "warn" : "bad"); }

function рисоватьТаблицу() {
  const tb = document.getElementById("tbody");
  tb.innerHTML = "";
  for (const s of ДАННЫЕ) {
    if (выбрана && s.к !== выбрана) continue;
    const tr = document.createElement("tr");
    const авто = s.чел === 0;
    tr.innerHTML =
      '<td>' + s.у + '</td>' +
      '<td><span class="tag ' + (авто ? "auto" : "hand") + '">' + (авто ? "автомат" : "с проверкой") + '</span></td>' +
      '<td>' + s.м + '</td>' +
      '<td class="num">' + Math.round(s.вх / 1000) + 'k</td>' +
      '<td class="num">' + (авто ? "—" : s.чел + " мин") + '</td>' +
      '<td class="num">$' + s.т.toFixed(2) + '</td>' +
      '<td class="num price">$' + s.пулы[пул].цена +
        (s.пулы[пул].скидка ? ' <s style="color:var(--ink-faint);font-weight:400">$' + s.ц + '</s>' : '') +
        (s.пулы[пул].урезана ? ' <span title="скидка урезана пределом" style="color:var(--warn)">▲</span>' : '') +
      '</td>' +
      '<td class="num cov ' + классПокрытия(s.покр) + '">' + s.покр + '×</td>';
    tb.appendChild(tr);
  }
}

function считать() {
  const вх = (+document.getElementById("ctx").value || 0) * 1000;
  const вых = (+document.getElementById("out").value || 0) * 1000;
  const [ци, цо] = document.getElementById("mdl").value.split(",").map(Number);
  const мин = +document.getElementById("hum").value || 0;
  const себ = (вх * ци + вых * цо) / 1e6 * 1.25;
  const чел = мин / 60 * 60;
  let ц = Math.max((себ + чел) * 2.2, себ * 5 + чел);
  ц = ц < 10 ? Math.ceil(ц) : (ц < 100 ? Math.ceil(ц / 5) * 5 : Math.ceil(ц / 25) * 25);
  const покр = себ > 0 ? (ц * 0.9 / себ) : 0;
  document.getElementById("out-calc").innerHTML =
    '<span class="big">$' + ц + '</span>' +
    '<span class="sub">себестоимость токенов $' + себ.toFixed(3) +
    ' · покрытие после комиссии ' + покр.toFixed(1) + '×' +
    (мин ? ' · время человека $' + чел.toFixed(0) : ' · без участия человека') + '</span>';
}

for (const id of ["ctx", "out", "mdl", "hum"]) {
  document.getElementById(id).addEventListener("input", считать);
}
рисоватьПулы(); рисоватьФильтры(); рисоватьТаблицу(); считать();
</script>
"""

пулы_табл = "".join(
    '<tr><td>%s</td><td>%s</td><td class="num">%d %%</td><td class="num">%d</td>'
    '<td class="num price">$%d</td></tr>' % (имя, описание, round(скидка * 100),
                                             урезано[имя], суммы[имя])
    for имя, описание, скидка in ПУЛЫ)

HTML = (HTML.replace("__ПУЛЫ__", json.dumps(ПУЛЫ, ensure_ascii=False))
            .replace("__ПУЛЫ_ТАБЛИЦА__", пулы_табл)
            .replace("__ДАННЫЕ__", данные)
            .replace("__КАТЕГОРИИ__", json.dumps(категории, ensure_ascii=False))
            .replace("__ВСЕГО__", str(len(строки)))
            .replace("__АВТО__", str(len(авто)))
            .replace("__МИНПОКР__", str(round(мин_покр, 1))))

io.open(os.path.join(ЗДЕСЬ, "index.html"), "w", encoding="utf-8").write(HTML)
print("страница собрана:", len(HTML), "знаков |", len(строки), "позиций,",
      len(авто), "автоматических,", len(с_чел), "с проверкой")
