# -*- coding: utf-8 -*-
"""Квитанция приёмки материалов: то, что заказчик получает на руки.

Берёт mediacheck_receipt.json и делает страницу, которую можно открыть в браузере
и переслать. Смысл квитанции не в том, чтобы поставить оценку, а в том, чтобы
заказчик и подрядчик спорили о числах, а не о впечатлении.

Запуск:
    python mediacheck.py папка_с_материалами
    python receipt.py mediacheck_receipt.json "Название работы" [--скрыть-имена]

--скрыть-имена заменяет имена файлов на «материал 01, 02…»: имена часто содержат
названия проектов и клиентов, а квитанция ходит по почте.
"""
import html, io, json, os, sys, time

ПОРОГ_ДЕТАЛИ = 0.70      # ниже — предупреждение о мягкой картинке
ПОРОГ_ПОВТОРОВ = 0.40    # выше — предупреждение о повторяющихся кадрах
ПОРОГ_ЗВУКА = 14000      # Гц, ниже — предупреждение о срезанной полосе


def вердикт(с):
    зам = []
    д = с.get("доля_детали")
    if д is not None and д < ПОРОГ_ДЕТАЛИ:
        зам.append("деталь доходит только до %d %% от заявленного размера" % round(д * 100))
    п = с.get("повторов_доля")
    if п is not None and п > ПОРОГ_ПОВТОРОВ:
        зам.append("%d %% соседних кадров неотличимы друг от друга" % round(п * 100))
    зп = с.get("звук_предел_гц")
    if зп is not None and зп < ПОРОГ_ЗВУКА:
        зам.append("спектр звука обрывается на %.1f кГц" % (зп / 1000.0))
    if с.get("ошибка"):
        зам.append("файл не прочитан: %s" % с["ошибка"])
    return зам


def строка(н, с, скрыть):
    имя = ("материал %02d" % н) if скрыть else с.get("файл", "")
    зам = вердикт(с)
    д = с.get("доля_детали")
    клетки = [
        html.escape(имя),
        html.escape(str(с.get("тип") or "")),
        html.escape(str(с.get("заявлено") or "—")),
        html.escape(str(с.get("измерено") or "—")),
        ("%d %%" % round(д * 100)) if д is not None else "—",
        ("%d %%" % round(с["повторов_доля"] * 100)) if с.get("повторов_доля") is not None else "—",
        ("%.1f кГц" % (с["звук_предел_гц"] / 1000.0)) if с.get("звук_предел_гц") else "—",
    ]
    цвет = "warn" if зам else "ok"
    подпись = "<br>".join("<span class=\"z\">" + html.escape(x) + "</span>" for x in зам) or \
              "<span class=\"z ok\">расхождений не найдено</span>"
    return ("<tr class=\"%s\"><td>%s<div class=\"sub\">%s</div></td>" % (цвет, клетки[0], подпись)
            + "".join("<td class=\"num\">%s</td>" % k for k in клетки[1:]) + "</tr>")


ШАБЛОН = """<title>Квитанция приёмки материалов</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@600;700&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root { --g:#f8f7f4; --p:#fff; --l:#dedad2; --ls:#eeeae2; --i:#1c1a17; --is:#57524a; --if:#8a8279;
        --ok:#2f6b3f; --warn:#8a6a00; --acc:#9a5b00; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --g:#151412; --p:#1e1d1a; --l:#35322c; --ls:#292724; --i:#f0ece4; --is:#b4ada2; --if:#7d766c;
  --ok:#74b585; --warn:#d8b055; --acc:#e0a24a; } }
:root[data-theme="dark"] { --g:#151412; --p:#1e1d1a; --l:#35322c; --ls:#292724; --i:#f0ece4;
  --is:#b4ada2; --if:#7d766c; --ok:#74b585; --warn:#d8b055; --acc:#e0a24a; }
*{box-sizing:border-box}
body{margin:0;background:var(--g);color:var(--i);font-family:"Source Sans 3",system-ui,sans-serif;line-height:1.55}
.w{max-width:1040px;margin:0 auto;padding-block:40px 64px;padding-left:20px;padding-right:20px}
h1{font-family:"Zilla Slab",Georgia,serif;font-size:clamp(26px,4.5vw,40px);margin:0;line-height:1.12;text-wrap:balance}
h2{font-family:"Zilla Slab",Georgia,serif;font-size:clamp(18px,2.6vw,23px);margin:44px 0 0}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--if);margin-bottom:12px}
p{color:var(--is);max-width:68ch}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;background:var(--ls);border:1px solid var(--l);margin-top:28px}
.fact{background:var(--p);padding:16px 18px}
.fact b{display:block;font-family:"IBM Plex Mono",monospace;font-size:24px;font-weight:600;font-variant-numeric:tabular-nums}
.fact span{font-size:13px;color:var(--if)}
.box{overflow-x:auto;border:1px solid var(--l);background:var(--p);margin-top:18px}
table{border-collapse:collapse;width:100%;min-width:760px;font-size:14.5px}
th{text-align:left;font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;
   color:var(--if);font-weight:400;padding:12px 14px;border-bottom:1px solid var(--l);white-space:nowrap}
td{padding:12px 14px;border-bottom:1px solid var(--ls);vertical-align:top}
td.num{text-align:right;white-space:nowrap;font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}
tr.warn td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
tr.ok td:first-child{box-shadow:inset 3px 0 0 var(--ok)}
.sub{margin-top:5px;font-size:12.5px;color:var(--warn)}
.sub .ok{color:var(--ok)}
ul{color:var(--is);max-width:68ch} li{margin:6px 0}
.note{font-size:13.5px;color:var(--if);margin-top:12px}
code{font-family:"IBM Plex Mono",monospace;font-size:13px}
</style>
<div class="w">
  <div class="eyebrow">квитанция приёмки · __ДАТА__</div>
  <h1>__НАЗВАНИЕ__</h1>
  <p>Измерено то, что лежит внутри файлов, а не то, что записано в их свойствах.
  Числа ниже воспроизводимы: инструмент открыт, метод описан, проверка прибора
  встроена и печатается при каждом запуске.</p>

  <div class="facts">
    <div class="fact"><b>__ВСЕГО__</b><span>материалов проверено</span></div>
    <div class="fact"><b>__ЧИСТО__</b><span>без расхождений</span></div>
    <div class="fact"><b>__ЗАМЕЧ__</b><span>с замечаниями</span></div>
  </div>

  <h2>По каждому материалу</h2>
  <div class="box"><table>
    <thead><tr><th>Материал</th><th class="num">Тип</th><th class="num">Заявлено</th>
    <th class="num">Измерено</th><th class="num">Деталь</th><th class="num">Повторы</th>
    <th class="num">Звук до</th></tr></thead>
    <tbody>__СТРОКИ__</tbody>
  </table></div>

  <h2>Как читать</h2>
  <ul>
    <li><b>Измерено</b> — до какого размера в кадре есть настоящая деталь. Файл может
    быть 3840×2160, а деталь в нём как в 2160×1215.</li>
    <li><b>Повторы</b> — доля соседних кадров, неотличимых друг от друга. Высокое
    значение у статичной сцены нормально, у движения — нет.</li>
    <li><b>Звук до</b> — где обрывается спектр. 48 кГц в заголовке и 12 кГц в звуке
    встречаются в одном файле.</li>
  </ul>

  <h2>Чего эта квитанция не утверждает</h2>
  <ul>
    <li>Что кто-то обманул. Сжатие съедает деталь без всякого обмана: честный рендер
    после обычного битрейта читается ниже своего размера.</li>
    <li>Что мягкая картинка была растянута. Расфокус и растяжение прибор не различает.</li>
    <li>Что материал плохой. Квитанция говорит, что доехало, а годится это или нет —
    решает тот, кто принимает работу.</li>
  </ul>
  <p class="note">Инструмент: <code>mediacheck</code>, github.com/ychkydyk/oneframe →
  tools/media. Проверка прибора: <code>python mediacheck.py --selftest</code> — печатает
  показания на образцах с заранее известным ответом.</p>
</div>"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    путь = sys.argv[1]
    название = sys.argv[2] if len(sys.argv) > 2 else "Приёмка материалов"
    скрыть = "--скрыть-имена" in sys.argv

    сырое = json.load(io.open(путь, encoding="utf-8"))
    строки_данных = сырое["строки"] if isinstance(сырое, dict) else сырое

    с_зам = [с for с in строки_данных if вердикт(с)]
    тело = "".join(строка(i + 1, с, скрыть) for i, с in enumerate(строки_данных))

    из_ = (ШАБЛОН.replace("__ДАТА__", time.strftime("%d.%m.%Y"))
                 .replace("__НАЗВАНИЕ__", html.escape(название))
                 .replace("__ВСЕГО__", str(len(строки_данных)))
                 .replace("__ЧИСТО__", str(len(строки_данных) - len(с_зам)))
                 .replace("__ЗАМЕЧ__", str(len(с_зам)))
                 .replace("__СТРОКИ__", тело))
    выход = os.path.splitext(путь)[0] + "_receipt.html"
    io.open(выход, "w", encoding="utf-8").write(из_)
    print("квитанция:", выход, "| материалов:", len(строки_данных),
          "| с замечаниями:", len(с_зам))
    return 0


if __name__ == "__main__":
    sys.exit(main())
