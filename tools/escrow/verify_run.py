# -*- coding: utf-8 -*-
"""Прогон проверок #46172 на локальной цепи: правильный деплой и заведомо плохой.

Правильный — Safe 2 из 3, обязан пройти все пункты.
Плохой — Safe с порогом 1: одна подпись двигает всё. Обязан быть ОТКЛОНЁН.
Если плохой проходит, проверяльщик бесполезен, и «правильный прошёл» ничего не значит.
"""
import io, json, os, sys

from eth_account import Account
from web3 import Web3, EthereumTesterProvider

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_deploy import артефакт, проверить

НОЛЬ = "0x0000000000000000000000000000000000000000"


def развернуть(w3, казна, владельцы, порог):
    safe_art = артефакт("Safe.sol/Safe.json")
    fac_art = артефакт("proxies/SafeProxyFactory.sol/SafeProxyFactory.json")

    S = w3.eth.contract(abi=safe_art["abi"], bytecode=safe_art["bytecode"])
    tx1 = S.constructor().transact({"from": казна, "gas": 6_000_000})
    r1 = w3.eth.wait_for_transaction_receipt(tx1)

    F = w3.eth.contract(abi=fac_art["abi"], bytecode=fac_art["bytecode"])
    tx2 = F.constructor().transact({"from": казна, "gas": 3_000_000})
    r2 = w3.eth.wait_for_transaction_receipt(tx2)
    factory = w3.eth.contract(address=r2.contractAddress, abi=fac_art["abi"])

    setup = w3.eth.contract(abi=safe_art["abi"]).encode_abi(
        "setup", args=[владельцы, порог, НОЛЬ, b"", НОЛЬ, НОЛЬ, 0, НОЛЬ])
    tx3 = factory.functions.createProxyWithNonce(r1.contractAddress, setup, 7).transact(
        {"from": казна, "gas": 3_000_000})
    r3 = w3.eth.wait_for_transaction_receipt(tx3)
    прокси = factory.events.ProxyCreation().process_receipt(r3)[0]["args"]["proxy"]
    return {"singleton": r1.contractAddress, "factory": r2.contractAddress, "safe": прокси,
            "tx": {"singleton": tx1, "factory": tx2, "сделка": tx3}}


def main():
    w3 = Web3(EthereumTesterProvider())
    казна = w3.eth.accounts[0]
    роли = [Account.create() for _ in range(3)]
    владельцы = sorted([a.address for a in роли], key=lambda x: int(x, 16))

    хор = развернуть(w3, казна, владельцы, 2)
    _, ок_хор = проверить(w3, w3.eth.chain_id, хор["safe"], хор["singleton"], хор["factory"],
                          хор["tx"], владельцы, 2, метка="ПРАВИЛЬНЫЙ: 2 из 3")

    плох = развернуть(w3, казна, владельцы, 1)
    _, ок_плох = проверить(w3, w3.eth.chain_id, плох["safe"], плох["singleton"], плох["factory"],
                           плох["tx"], владельцы, 1, метка="КОНТРОЛЬ: порог 1, выпускать нельзя")

    # контроль: прокси стоит на ЧУЖОМ singleton при верных владельцах и пороге
    чужой_singleton = развернуть(w3, казна, владельцы, 2)["singleton"]
    _, ок_подмена = проверить(w3, w3.eth.chain_id, хор["safe"], чужой_singleton, хор["factory"],
                              хор["tx"], владельцы, 2, метка="КОНТРОЛЬ: подменён singleton")

    # ещё один контроль: та же сделка, но заявлена не та сеть
    _, ок_сеть = проверить(w3, w3.eth.chain_id + 1, хор["safe"], хор["singleton"], хор["factory"],
                           хор["tx"], владельцы, 2, метка="КОНТРОЛЬ: объявлена чужая сеть")

    print("\n" + "=" * 62)
    print("  правильный деплой прошёл:            ", "да" if ок_хор else "НЕТ")
    print("  порог 1 отклонён:                    ", "да" if not ок_плох else "НЕТ — проверяльщик слеп")
    print("  чужой CHAIN_ID отклонён:             ", "да" if not ок_сеть else "НЕТ — проверяльщик слеп")
    print("  подмена singleton отклонена:         ", "да" if not ок_подмена else "НЕТ — проверяльщик слеп")
    годен = ок_хор and not ок_плох and not ок_сеть and not ок_подмена
    print("  ВЫВОД:", "проверяльщик различает хорошее и плохое" if годен else "ПРОВЕРЯЛЬЩИК НЕГОДЕН")
    print("=" * 62)


if __name__ == "__main__":
    main()
