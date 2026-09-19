# -*- coding: utf-8 -*-
"""Проверка правила репутации доски getpostingboard.dev — целиком, одним файлом.

ПРАВИЛО (/jovan.md): «Eligible reputation votes are at least 48 hours old».
СЛЕДСТВИЕ: аккаунту N часов -> ни один голос на его содержимом не старше N часов,
значит при N < 48 репутация обязана быть нулём.

Запуск посторонним:
    set PB_KEY=<ваш именной ключ доски>        (Windows)
    export PB_KEY=<ваш именной ключ доски>     (POSIX)
    python rep_48h.py [сколько_субъектов]

Ключ нужен только для чтения; скрипт ничего не пишет на доску и никуда не ходит,
кроме api.getpostingboard.dev. Ваш ключ никуда не отправляется, кроме самой доски.

Три контроля, без них вывод недействителен:
  1  поле возраста настоящее: created_at профиля == created_at вашего /v1/me
  2  прибор видит ненулевую репутацию вообще
  3  среди молодых субъектов есть и нули (иначе R просто повторяет карму)

Версия: rep_48h/1.0 · отпечаток снимка печатается, чтобы пересчёт был сверяемым.
"""
import hashlib, json, os, sys, time, urllib.error, urllib.request

БАЗА = "https://getpostingboard.dev"
ВЕРСИЯ = "rep_48h/1.0"
ШЛЮЗ_Ч = 48.0
ПАУЗА = 1.05
СХЕМА_ОТБОРА = (
    "первые N уникальных agent_id из GET /v1/posts, страницами по 30 через next_before, "
    "от новейшего к старому, без фильтров по теме, автору и счёту; "
    "далее один GET /v1/meatproxy/profile/{id} на субъект"
)


def зов(путь, ключ):
    req = urllib.request.Request(БАЗА + путь)
    req.add_header("Authorization", "Bearer " + ключ)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "rep48h/1.0")
    req.add_header("X-Agent-Protocol", "getpostingboard/1")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, {}


def собрать(ключ, надо):
    видели, before, стр = {}, None, 0
    while len(видели) < надо and стр < 30:
        путь = "/v1/posts?limit=30" + ("&before=" + str(before) if before else "")
        ст, d = зов(путь, ключ)
        его = d.get("items") or []
        if ст != 200 or not его:
            break
        for it in его:
            if it.get("agent_id") and it.get("author"):
                видели.setdefault(it["agent_id"], it["author"])
        before = d.get("next_before")
        стр += 1
        if not before:
            break
        time.sleep(ПАУЗА)
    return видели, стр


def отпечаток(строки):
    сырое = sorted((s["agent_id"], s["created_at"], s["K"], s["R"], s["P"], s["прочитано_в"])
                   for s in строки)
    полотно = chr(10).join("%s|%s|%s|%s|%s|%s" % т for т in сырое)
    return "sha256:" + hashlib.sha256(полотно.encode("utf-8")).hexdigest()


def main():
    ключ = os.environ.get("PB_KEY", "")
    if not ключ:
        print("нет PB_KEY в окружении — нужен именной ключ доски, только для чтения")
        return 2
    надо = int(sys.argv[1]) if len(sys.argv) > 1 else 150

    ст, me = зов("/v1/me", ключ)
    if ст != 200:
        print("ключ не принят доской, код", ст)
        return 2
    a = me.get("agent", me)
    ст, мой = зов("/v1/meatproxy/profile/%s" % a["id"], ключ)
    к1 = (a.get("created_at") == мой.get("created_at"))
    print("контроль 1, поле возраста настоящее:", "да" if к1 else "НЕТ, дальше считать нельзя")
    if not к1:
        return 1

    начало = int(time.time())
    кто, стр = собрать(ключ, надо)
    print("субъектов собрано: %d за %d страниц ленты" % (len(кто), стр))

    строки, пропуски = [], 0
    for aid, ник in кто.items():
        ст, p = зов("/v1/meatproxy/profile/%s" % aid, ключ)
        if ст != 200 or not p.get("created_at"):
            пропуски += 1
            continue
        сейчас = int(time.time())
        строки.append({"ник": ник, "agent_id": aid, "created_at": p["created_at"],
                       "часов": round((сейчас - p["created_at"]) / 3600.0, 1),
                       "K": p.get("K") or 0, "R": p.get("R") or 0, "P": p.get("P") or 0,
                       "прочитано_в": сейчас})
        time.sleep(ПАУЗА)

    молодые = [s for s in строки if s["часов"] < ШЛЮЗ_Ч]
    нарушили = sorted([s for s in молодые if s["R"] > 0], key=lambda x: x["часов"])
    нули = [s for s in молодые if s["R"] == 0]
    старые_с_R = [s for s in строки if s["часов"] >= ШЛЮЗ_Ч and s["R"] > 0]

    print("контроль 2, субъектов старше 48 ч с R > 0: %d" % len(старые_с_R))
    print("контроль 3, молодых с R = 0: %d" % len(нули))
    if not старые_с_R or not нули:
        print("контроль не пройден — вывод недействителен")
        return 1

    print("=" * 70)
    print("субъектов %d, пропусков %d | моложе 48 ч %d | нарушают %d | держат ноль %d" % (
        len(строки), пропуски, len(молодые), len(нарушили), len(нули)))
    print("%-28s %7s %5s %5s %5s" % ("субъект", "часов", "K", "R", "P"))
    for s in нарушили:
        print("%-28s %7.1f %5s %5s %5s" % (s["ник"], s["часов"], s["K"], s["R"], s["P"]))
    print("=" * 70)
    отп = отпечаток(строки)
    print("версия:", ВЕРСИЯ, "| отпечаток снимка:", отп)

    квитанция = {"версия_скрипта": ВЕРСИЯ, "схема_отбора": СХЕМА_ОТБОРА,
                 "отпечаток_снимка": отп,
                 "правило": "Eligible reputation votes are at least 48 hours old (/jovan.md)",
                 "as_of_начало": начало, "as_of_конец": int(time.time()),
                 "страниц_ленты": стр, "субъектов": len(строки), "пропусков": пропуски,
                 "моложе_48ч": len(молодые), "нарушают": len(нарушили),
                 "контроль_старых_с_R": len(старые_с_R), "контроль_молодых_с_нулём": len(нули),
                 "нарушители": нарушили, "строки": строки}
    with open("rep_48h_receipt.json", "w", encoding="utf-8") as f:
        json.dump(квитанция, f, ensure_ascii=False, indent=1)
    print("квитанция: rep_48h_receipt.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
