from __future__ import annotations
import json
from chain import Blockchain, Transaction, TxType


def load_run(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_ledger(run: dict):
    bc = Blockchain(difficulty=2)
    for n in run["nodes"]:
        if n.get("parent"):
            bc.stage(Transaction(sender=n["parent"], recipient=n["id"], amount=n["fromParent"], type=TxType.FUNDING, meta={"award_date": n.get("awardDate")}))
        if n.get("markup"):
            bc.stage(Transaction(sender=n.get("parent"), recipient=n["id"], amount=n["fromParent"], type=TxType.PROCUREMENT, good_id="contract:" + n["id"], qty=1, unit_price=round(1 + n["markup"], 4)))
        for t in n.get("transfers", []):
            bc.stage(Transaction(sender=n["id"], recipient=t["to"], amount=n["kickedOut"], type=TxType.KICKBACK, meta={"rate": t["rate"]}))
    bc.mine()

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
    return bc, entities, truth
