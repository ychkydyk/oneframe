# -*- coding: utf-8 -*-
"""Фикстура для пилотной сделки: поток событий, часть строк намеренно испорчена.

Задача пилота устроена вокруг того самого класса ошибок, который мы за сутки нашли
в трёх разных артефактах: система не смогла разобрать вход и промолчала об этом.
Поэтому здесь проверяется не «умеет ли разбирать», а **говорит ли вслух, чего не
смогла разобрать**.

Генератор детерминирован: одно и то же семя даёт один и тот же файл побайтово.
Публикуется семя 1 (открытая фикстура) и sha256 спецификации; приёмка идёт на
семени 2, которое до сдачи не публикуется.

Запуск:
    python make_fixture.py 1 open.jsonl
    python make_fixture.py 2 hidden.jsonl
"""
import hashlib, json, random, sys

ТИПЫ = ["view", "click", "purchase", "error", "heartbeat"]
ВСЕГО = 200

ПОРЧИ = [
    "truncated",      # строка обрезана посередине
    "not_json",       # вообще не json
    "wrong_type",     # amount строкой вместо числа
    "missing_field",  # нет обязательного поля type
    "bad_utf8",       # байт, который не декодируется
]


def сделать(семя, путь):
    сл = random.Random(семя)
    строки, ожидание = [], {"по_типам": {}, "испорчено": {}, "всего_строк": ВСЕГО}
    for i in range(ВСЕГО):
        порча = ПОРЧИ[сл.randrange(len(ПОРЧИ))] if сл.random() < 0.18 else None
        тип = ТИПЫ[сл.randrange(len(ТИПЫ))]
        запись = {"id": i, "type": тип, "amount": round(сл.uniform(0, 100), 2),
                  "ts": 1789800000 + i * 7}
        сырое = json.dumps(запись, ensure_ascii=False)

        if порча is None:
            ожидание["по_типам"][тип] = ожидание["по_типам"].get(тип, 0) + 1
            строки.append(сырое.encode("utf-8"))
            continue

        ожидание["испорчено"][порча] = ожидание["испорчено"].get(порча, 0) + 1
        if порча == "truncated":
            строки.append(сырое[: len(сырое) // 2].encode("utf-8"))
        elif порча == "not_json":
            строки.append(("это не json, строка " + str(i)).encode("utf-8"))
        elif порча == "wrong_type":
            з = dict(запись, amount=str(запись["amount"]))
            строки.append(json.dumps(з, ensure_ascii=False).encode("utf-8"))
        elif порча == "missing_field":
            з = dict(запись)
            del з["type"]
            строки.append(json.dumps(з, ensure_ascii=False).encode("utf-8"))
        elif порча == "bad_utf8":
            строки.append(сырое.encode("utf-8") + b"\xff\xfe")

    данные = b"\n".join(строки) + b"\n"
    with open(путь, "wb") as f:
        f.write(данные)
    ожидание["разобрано"] = sum(ожидание["по_типам"].values())
    ожидание["не_разобрано"] = sum(ожидание["испорчено"].values())
    ожидание["sha256_файла"] = hashlib.sha256(данные).hexdigest()
    return ожидание


if __name__ == "__main__":
    семя = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    путь = sys.argv[2] if len(sys.argv) > 2 else "fixture.jsonl"
    о = сделать(семя, путь)
    print(json.dumps(о, ensure_ascii=False, indent=1))
