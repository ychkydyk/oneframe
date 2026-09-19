# -*- coding: utf-8 -*-
"""Поправка misha-agent-0002 (#46172): отделить «контракт Safe известной версии»
от «именно этот деплой имеет ожидаемую конфигурацию».

Пять проверок перед тем, как публиковать адрес сделки:
  1  CHAIN_ID   сеть та, что заявлена, а не похожая
  2  РАЗВЁРНУТ  по адресу вообще есть код
  3  БАЙТКОД    keccak runtime-кода singleton и factory == официальный артефакт
  4  ДАЙДЖЕСТЫ  хеши транзакций деплоя зафиксированы и опубликованы
  5  ЧТЕНИЕ     owners и threshold прочитаны заново с адреса, а не взяты из памяти

Контроль обязателен: проверяльщик обязан ОТКАЗАТЬ заведомо неправильной сделке.
Здесь известно-отрицательный случай — второй Safe с порогом 1: одна подпись двигает
всё, и именно такой деплой нельзя выпускать в люди. Если проверяльщик его пропустил,
его вывод о правильном деплое ничего не стоит.
"""
import io, json, os, sys

from eth_utils import keccak
from web3 import Web3

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "contracts", "package", "build", "artifacts", "contracts")


def артефакт(путь):
    return json.load(io.open(os.path.join(ART, путь), encoding="utf-8"))


def хеш_кода(hexstr):
    b = bytes.fromhex(hexstr[2:] if hexstr.startswith("0x") else hexstr)
    return "0x" + keccak(b).hex() if not isinstance(keccak(b), str) else keccak(b)


def коротко_адрес(a):
    return a[:10] + "..." + a[-6:]


def к_хексу(x):
    return x if isinstance(x, str) else "0x" + x.hex()


def проверить(w3, ожидаемый_chain_id, адрес_safe, singleton, factory,
              deploy_tx, ожидаемые_владельцы, ожидаемый_порог, метка=""):
    """Возвращает (список строк отчёта, всё ли сошлось)."""
    отчёт, всё = [], True

    def пункт(имя, ок, деталь):
        nonlocal всё
        всё = всё and ок
        отчёт.append((имя, "сошлось" if ок else "НЕ СОШЛОСЬ", деталь))

    # 1 сеть
    cid = w3.eth.chain_id
    пункт("CHAIN_ID", cid == ожидаемый_chain_id, "%s, ожидали %s" % (cid, ожидаемый_chain_id))

    # 2 код по адресу есть
    код_safe = w3.eth.get_code(Web3.to_checksum_address(адрес_safe))
    пункт("код по адресу сделки", len(код_safe) > 0, "%d байт" % len(код_safe))

    # 3 байткод singleton и factory против официальных артефактов
    пары = [("singleton", singleton, артефакт("Safe.sol/Safe.json")),
            ("factory", factory, артефакт("proxies/SafeProxyFactory.sol/SafeProxyFactory.json"))]
    for имя, адрес, art in пары:
        живой = w3.eth.get_code(Web3.to_checksum_address(адрес))
        ждали = bytes.fromhex(art["deployedBytecode"][2:])
        h1, h2 = keccak(живой), keccak(ждали)
        пункт("байткод %s" % имя, h1 == h2, "keccak %s" % к_хексу(h1)[:18])

    # 4 дайджесты транзакций деплоя
    цепочка_ок = True
    детали = []
    for имя, tx in deploy_tx.items():
        r = w3.eth.get_transaction_receipt(tx)
        ок = (r["status"] == 1)
        цепочка_ок = цепочка_ок and ок
        детали.append("%s %s блок %s" % (имя, к_хексу(tx)[:12], r["blockNumber"]))
    пункт("транзакции деплоя", цепочка_ок, "; ".join(детали))

    # 5 прокси обязан стоять на НАШЕМ singleton, а не на похожем
    # (владельцы и порог могут выглядеть верно у прокси, делегирующего чужой код)
    слот = w3.eth.get_storage_at(Web3.to_checksum_address(адрес_safe), 0)
    мастер = "0x" + слот.hex()[-40:]
    пункт("singleton под прокси", мастер.lower() == singleton.lower(),
          "слот 0 -> %s" % коротко_адрес(мастер))

    # 6 независимое перечитывание конфигурации С АДРЕСА, а не из памяти
    abi = артефакт("Safe.sol/Safe.json")["abi"]
    safe = w3.eth.contract(address=Web3.to_checksum_address(адрес_safe), abi=abi)
    вл = [w.lower() for w in safe.functions.getOwners().call()]
    пор = safe.functions.getThreshold().call()
    пункт("владельцы прочитаны с адреса", sorted(вл) == sorted(w.lower() for w in ожидаемые_владельцы),
          "%d шт." % len(вл))
    пункт("порог прочитан с адреса", пор == ожидаемый_порог, "%s, ожидали %s" % (пор, ожидаемый_порог))
    # отдельным пунктом: порог 1 нельзя выпускать никогда, каким бы ожидаемым он ни был
    пункт("порог больше единицы", пор >= 2, "порог %s" % пор)

    print("\n=== проверка деплоя %s ===" % метка)
    for имя, вердикт, деталь in отчёт:
        print("  %-30s %-12s %s" % (имя, вердикт, деталь))
    print("  ВЕРДИКТ:", "адрес можно публиковать" if всё else "ПУБЛИКОВАТЬ НЕЛЬЗЯ")
    return отчёт, всё
