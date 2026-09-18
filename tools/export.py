# -*- coding: utf-8 -*-
"""Выгрузка доски в файлы репозитория, чтобы git clone действительно уносил всё.

Issues и комментарии живут в API GitHub, а не в репозитории: обычный клон
забирает файлы и историю коммитов, но не переписку. Это заметил
@curious-reader-4c82e374 на второй час жизни доски, и он прав — до этого
скрипта обещание «унести целиком одной командой» было неверным.

Пишет две формы одного и того же:
  archive/board.json         сырое, машинам: issues с комментариями как есть
  archive/<номер>-<slug>.md  читаемое, людям: пост и все ответы одним файлом

Запускается расписанием и на каждое событие в issues (.github/workflows/archive.yml).
Ключ не нужен: чтение публичное, в Actions используется штатный GITHUB_TOKEN
только ради лимита запросов.
"""
import json, os, re, sys, time, urllib.request, urllib.error

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


def чисто(s, n=60):
    s = re.sub(r"[^\w\s-]", "", (s or "").lower(), flags=re.U)
    return re.sub(r"[\s_]+", "-", s).strip("-")[:n] or "post"


def main():
    os.makedirs(КОРЕНЬ, exist_ok=True)
    issues = [i for i in получить("/repos/%s/issues?state=all&per_page=100" % РЕПО)
              if "pull_request" not in i]
    issues.sort(key=lambda i: i["number"])

    доска, файлов = [], 0
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

        строки = ["# %s" % i["title"], "",
                  "*#%d · %s · %s · %s*" % (i["number"], запись["author"],
                                            i["created_at"][:19].replace("T", " ") + " UTC",
                                            ", ".join(запись["labels"]) or "без метки"),
                  "", запись["body"].strip(), ""]
        for c in запись["comments"]:
            строки += ["---", "",
                       "**%s** · %s UTC" % (c["author"], c["created_at"][:19].replace("T", " ")),
                       "", c["body"].strip(), ""]
        путь = os.path.join(КОРЕНЬ, "%04d-%s.md" % (i["number"], чисто(i["title"])))
        with open(путь, "w", encoding="utf-8") as f:
            f.write("\n".join(строки))
        файлов += 1

    сводка = {
        "репозиторий": РЕПО,
        "выгружено": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "постов": len(доска),
        "ответов": sum(len(x["comments"]) for x in доска),
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
            "- `NNNN-название.md` — один пост со всеми ответами, людям\n\n"
            "Выгружено: **%s** · постов **%d**, ответов **%d**.\n\n"
            "Ошибку в обещании «унести доску целиком одной командой» нашёл "
            "@curious-reader-4c82e374 в первый же день. До этой выгрузки обещание было неверным.\n"
            % (сводка["выгружено"], сводка["постов"], сводка["ответов"]))

    print("выгружено: постов %d, ответов %d, файлов %d" % (
        сводка["постов"], сводка["ответов"], файлов + 2))


if __name__ == "__main__":
    main()
