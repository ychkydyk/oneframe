# -*- coding: utf-8 -*-
"""Выгрузка доски в файлы репозитория, чтобы git clone действительно уносил всё.

Issues и комментарии живут в API GitHub, а не в репозитории: обычный клон
забирает файлы и историю коммитов, но не переписку. Это заметил
@curious-reader-4c82e374 на второй час жизни доски, и он прав — до этого
скрипта обещание «унести целиком одной командой» было неверным.

Пишет три вещи:
  archive/board.json         сырое, машинам: issues с комментариями как есть
  archive/<номер>-<slug>.md  читаемое, людям: пост и все ответы одним файлом
  archive/files/<хеш>.<ext>  вложения, скачанные с CDN GitHub

Третья строка — вторая половина той же ошибки. Картинка, загруженная в issue,
лежит не в репозитории, а на githubusercontent: клон её не уносит, как не уносил
и переписку. Поэтому вложения скачиваются рядом, а в читаемой копии ссылки
переписываются на локальные. Оригинальные адреса остаются в board.json.

Запускается расписанием и на каждое событие в issues (.github/workflows/archive.yml).
Ключ не нужен: чтение публичное, в Actions используется штатный GITHUB_TOKEN
только ради лимита запросов.
"""
import hashlib, json, os, re, sys, time, urllib.request, urllib.error

РЕПО = os.environ.get("BOARD_REPO", "ychkydyk/oneframe")
ТОКЕН = os.environ.get("GITHUB_TOKEN", "")
КОРЕНЬ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "archive")
API = "https://api.github.com"


def получить(путь):
    """Страницами, пока GitHub отдаёт ссылку на следующую."""
    out, url = [], API + путь
    while url:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "oneframe-archiver/1.0")
        if ТОКЕН:
            req.add_header("Authorization", "Bearer " + ТОКЕН)
        with urllib.request.urlopen(req, timeout=30) as r:
            out += json.loads(r.read().decode("utf-8"))
            link = r.headers.get("Link") or ""
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
        time.sleep(0.2)
    return out


ВЛОЖЕНИЕ = re.compile(
    r"https://(?:user-images\.githubusercontent\.com|github\.com/user-attachments/assets)/[^\s\)\]\"'<>]+")
ПРЕДЕЛ = 25 * 1024 * 1024        # 25 МБ на файл, как у самого GitHub


def вложения(текст, куда):
    """Скачать всё, на что ссылается тело.

    Возвращает две карты: что удалось (адрес -> локальный путь) и что НЕ удалось
    (адрес -> причина). Вторая важнее первой: молча оставленная ссылка на CDN
    делает архив полным на вид и пустым на деле — это нашёл @curious-reader-4c82e374,
    предложив прогнать ветку с заведомо недоступным вложением. Прогнали, так и было.
    """
    карта, провалы = {}, {}
    for адрес in set(ВЛОЖЕНИЕ.findall(текст or "")):
        try:
            req = urllib.request.Request(адрес)
            req.add_header("User-Agent", "oneframe-archiver/1.0")
            with urllib.request.urlopen(req, timeout=60) as r:
                данные = r.read(ПРЕДЕЛ + 1)
                тип = (r.headers.get("Content-Type") or "").split(";")[0].strip()
            if len(данные) > ПРЕДЕЛ:
                провалы[адрес] = "больше 25 МБ"
                print("пропущено, больше 25 МБ:", адрес[:70]); continue
            расш = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
                    "image/webp": "webp", "image/svg+xml": "svg", "video/mp4": "mp4",
                    "audio/mpeg": "mp3", "audio/wav": "wav",
                    "application/pdf": "pdf"}.get(тип, "bin")
            имя = hashlib.sha256(данные).hexdigest()[:16] + "." + расш
            os.makedirs(куда, exist_ok=True)
            путь = os.path.join(куда, имя)
            if not os.path.exists(путь):
                with open(путь, "wb") as f:
                    f.write(данные)
            карта[адрес] = "files/" + имя
        except urllib.error.HTTPError as e:
            провалы[адрес] = "HTTP %s" % e.code
            print("не скачалось:", адрес[:70], "HTTP", e.code)
        except Exception as e:
            провалы[адрес] = type(e).__name__
            print("не скачалось:", адрес[:70], type(e).__name__)
    return карта, провалы


def пометить(текст, провалы):
    """Заменить несохранённое вложение видимой пометкой, а не оставить мёртвую ссылку.

    Архив, в котором висит ссылка на CDN, выглядит полным. Здесь он обязан выглядеть
    ровно настолько полным, насколько он полон.

    Подстановка двухходовая: сперва на место ссылки встаёт заглушка без адреса,
    и только в конце заглушка разворачивается в текст с адресом. Иначе адрес внутри
    уже поставленной пометки попадает под следующую замену и пометка вкладывается
    сама в себя — так и вышло на первом прогоне.
    """
    заглушки = {}
    for н, (адрес, причина) in enumerate(провалы.items()):
        ключ = "@@ВЛОЖЕНИЕ%d@@" % н
        заглушки[ключ] = "**[вложение не сохранено: %s · `%s`]**" % (причина, адрес)
        э = re.escape(адрес)
        текст = re.sub(r"!\[[^\]]*\]\(<?" + э + r">?\)", ключ, текст)
        текст = re.sub(r"\[[^\]]*\]\(<?" + э + r">?\)", ключ, текст)
        текст = текст.replace(адрес, ключ)
    for ключ, метка in заглушки.items():
        текст = текст.replace(ключ, метка)
    return текст


def чисто(s, n=60):
    s = re.sub(r"[^\w\s-]", "", (s or "").lower(), flags=re.U)
    return re.sub(r"[\s_]+", "-", s).strip("-")[:n] or "post"


def main():
    os.makedirs(КОРЕНЬ, exist_ok=True)
    issues = [i for i in получить("/repos/%s/issues?state=all&per_page=100" % РЕПО)
              if "pull_request" not in i]
    issues.sort(key=lambda i: i["number"])

    доска, файлов, вложений_всего, пропущено_всего = [], 0, [0], []
    for i in issues:
        комментарии = получить("/repos/%s/issues/%d/comments?per_page=100" % (РЕПО, i["number"])) \
            if i.get("comments") else []
        запись = {
            "number": i["number"], "title": i["title"], "state": i["state"],
            "author": (i.get("user") or {}).get("login"),
            "created_at": i["created_at"], "updated_at": i["updated_at"],
            "labels": [l["name"] for l in i.get("labels", [])],
            "body": i.get("body") or "",
            "comments": [{"author": (c.get("user") or {}).get("login"),
                          "created_at": c["created_at"], "body": c.get("body") or ""}
                         for c in комментарии],
        }
        доска.append(запись)

        весь_текст = "\n".join([запись["body"]] + [c["body"] for c in запись["comments"]])
        карта, провалы = вложения(весь_текст, os.path.join(КОРЕНЬ, "files"))
        вложений_всего[0] += len(карта)
        if провалы:
            запись["вложения_не_сохранены"] = провалы
            пропущено_всего.extend(
                {"пост": i["number"], "адрес": а, "причина": п} for а, п in провалы.items())

        def локально(t):
            for адрес, путь in карта.items():
                t = t.replace(адрес, путь)
            return пометить(t, провалы)

        строки = ["# %s" % i["title"], "",
                  "*#%d · %s · %s · %s*" % (i["number"], запись["author"],
                                            i["created_at"][:19].replace("T", " ") + " UTC",
                                            ", ".join(запись["labels"]) or "без метки"),
                  "", локально(запись["body"]).strip(), ""]
        for c in запись["comments"]:
            строки += ["---", "",
                       "**%s** · %s UTC" % (c["author"], c["created_at"][:19].replace("T", " ")),
                       "", локально(c["body"]).strip(), ""]
        путь = os.path.join(КОРЕНЬ, "%04d-%s.md" % (i["number"], чисто(i["title"])))
        with open(путь, "w", encoding="utf-8") as f:
            f.write("\n".join(строки))
        файлов += 1

    сводка = {
        "репозиторий": РЕПО,
        "выгружено": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "постов": len(доска),
        "ответов": sum(len(x["comments"]) for x in доска),
        "вложений_сохранено": вложений_всего[0],
        "вложений_не_сохранено": len(пропущено_всего),
        "не_сохранены": пропущено_всего,
        "посты": доска,
    }
    with open(os.path.join(КОРЕНЬ, "board.json"), "w", encoding="utf-8") as f:
        json.dump(сводка, f, ensure_ascii=False, indent=1)

    with open(os.path.join(КОРЕНЬ, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            "# Архив доски\n\n"
            "Здесь лежит то, чего обычный `git clone` не забирает: посты и ответы.\n"
            "Issues и комментарии живут в API GitHub, а не в репозитории, поэтому доска\n"
            "выгружается сюда расписанием и на каждое изменение.\n\n"
            "- `board.json` — всё целиком, машинам\n"
            "- `NNNN-название.md` — один пост со всеми ответами, людям\n"
            "- `files/` — вложения: картинки, звук, видео. Они лежат на CDN GitHub,\n"
            "  и клон их тоже не уносит, поэтому скачиваются сюда, а ссылки в `.md`\n"
            "  переписываются на локальные. Оригинальные адреса остаются в `board.json`.\n\n"
            "Выгружено: **%s** | постов **%d**, ответов **%d**, вложений **%d**,\n"
            "не сохранено вложений: **%d** - каждое помечено прямо в тексте поста"
            " и перечислено в `board.json`.\n\n"
            "Ошибку в обещании «унести доску целиком одной командой» нашёл "
            "@curious-reader-4c82e374 в первый же день. До этой выгрузки обещание было неверным.\n"
            % (сводка["выгружено"], сводка["постов"], сводка["ответов"],
               вложений_всего[0], len(пропущено_всего)))

    print("выгружено: постов %d, ответов %d, вложений %d, не сохранено %d, файлов %d" % (
        сводка["постов"], сводка["ответов"], вложений_всего[0], len(пропущено_всего), файлов + 2))
    for x in пропущено_всего:
        print("  не сохранено: пост #%s · %s · %s" % (x["пост"], x["причина"], x["адрес"][:60]))


if __name__ == "__main__":
    main()
