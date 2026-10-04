from __future__ import annotations
import json
from chain import Transaction, TxType
from consensus import Consortium


def load_run(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def entities_and_truth(run: dict):
    entities = {n["id"]: {
        "id": n["id"], "name": n["name"], "parent": n.get("parent"),
        "received": n["received"],
        "paid_out": n["down"] + n["kickedOut"] + n["delivered"],
        "linked_owner": n.get("linkedOwner"),
        "invoice_ratio": round(1 + n.get("markup", 0), 4),
        "transfers_out": [(t["to"], n["kickedOut"]) for t in n.get("transfers", [])],
        "trigger_event": n.get("triggerEvent"),
        "external_income": [(t["source"], t["amount"], t.get("return"), bool(t.get("linked")))
                    for t in n.get("externalIncome", [])],
        "tx_chunks": [(n["kickedOut"], t.get("chunks", 1)) for t in n.get("transfers", [])],
    } for n in run["nodes"]}
    truth = {n["id"]: {"label": n["label"], "schemes": n["schemes"]}
             for n in run["nodes"]}
    return entities, truth


def build_ledger(run: dict, validators: int = 5):
    cons = Consortium(n=validators, difficulty=2)
    txns = []
    for n in run["nodes"]:
        if n.get("parent"):
            txns.append(Transaction(sender=n["parent"], recipient=n["id"], amount=n["fromParent"],
                                    type=TxType.FUNDING, meta={"award_date": n.get("awardDate")}))
        if n.get("markup"):
            txns.append(Transaction(sender=n.get("parent"), recipient=n["id"], amount=n["fromParent"],
                                    type=TxType.PROCUREMENT, good_id="contract:" + n["id"], qty=1,
                                    unit_price=round(1 + n["markup"], 4)))
        for t in n.get("transfers", []):
            txns.append(Transaction(sender=n["id"], recipient=t["to"], amount=n["kickedOut"],
                                    type=TxType.KICKBACK, meta={"rate": t["rate"]}))
        for inc in n.get("externalIncome", []):
            txns.append(Transaction(sender=inc["source"], recipient=n["id"], amount=inc["amount"],
                                    type=TxType.ORACLE,
                                    meta={"return": inc.get("return"), "linked": bool(inc.get("linked"))}))
    cons.propose(txns)
    entities, truth = entities_and_truth(run)
    return cons, entities, truth
