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
        "delivered": n["delivered"],
        "cashed_out": n.get("cashedOut", 0.0),
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


def build_ledger(run: dict, validators: int = 5, journal=None):
    cons = Consortium(n=validators, difficulty=2)
    nodes = {n["id"]: n for n in run["nodes"]}
    txns = []
    seq = 0
    for e in run.get("events", []):
        if e["from"] is None:
            continue                       # the appropriation itself has no sender
        meta = {"kind": e["kind"], "depth": e["depth"], "ev_seq": e["seq"]}
        if "rate" in e:
            meta["rate"] = e["rate"]
        if "chunks" in e:
            meta["chunks"] = e["chunks"]
        if e["kind"] == "funding":
            meta["award_date"] = nodes.get(e["to"], {}).get("awardDate")
        txns.append(Transaction(sender=e["from"], recipient=e["to"], amount=e["amount"],
                                type={"transfer": TxType.KICKBACK, "cashout": TxType.CASHOUT}.get(e["kind"], TxType.FUNDING),
                                ts=float(seq), meta=meta))
        seq += 1

    for n in run["nodes"]:
        for inc in n.get("externalIncome", []):
            txns.append(Transaction(sender=inc["source"], recipient=n["id"], amount=inc["amount"],
                                    type=TxType.ORACLE, ts=float(seq),
                                    meta={"return": inc.get("return"), "linked": bool(inc.get("linked"))}))
            seq += 1

    if journal:
        for t in txns:
            journal.record(t)

    ok, votes = cons.propose(txns)
    if journal:
        journal.commit(cons.validators[0].chain.last.hash, [t.txid for t in txns], votes, ok)

    entities, truth = entities_and_truth(run)
    return cons, entities, truth
