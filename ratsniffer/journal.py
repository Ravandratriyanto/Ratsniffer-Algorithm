from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict

from chain import _sha

GENESIS = "0" * 64


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class Entry:
    seq: int
    kind: str          # "txn" | "commit"
    ts: float
    body: dict
    prev: str
    digest: str = ""

    def compute(self) -> str:
        return _sha(_canon({"seq": self.seq, "kind": self.kind, "ts": self.ts,
                            "body": self.body, "prev": self.prev}))

    def __post_init__(self):
        if not self.digest:
            self.digest = self.compute()


class Journal:
    """Append-only, hash-linked record of every transaction.

    Independent of the chain: no blocks, no merkle root, no proof-of-work, no
    consortium. Each line links to the one before it, so the file verifies on
    its own. Its value is being a *second* record of the same events — if the
    journal and the chain ever disagree, something was altered.
    """

    def __init__(self, path: str):
        self.path = path
        self.seq = 0
        self.prev = GENESIS
        for e in self.load():                      # resume an existing journal
            self.seq, self.prev = e.seq + 1, e.digest

    def _append(self, kind: str, ts: float, body: dict) -> Entry:
        e = Entry(seq=self.seq, kind=kind, ts=ts, body=body, prev=self.prev)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(_canon(asdict(e)) + "\n")
            f.flush()
        self.seq, self.prev = e.seq + 1, e.digest
        return e

    def record(self, txn) -> Entry:
        return self._append("txn", txn.ts, {
            "txid": txn.txid, "type": txn.type.value, "sender": txn.sender,
            "recipient": txn.recipient, "amount": txn.amount, "meta": txn.meta,
        })

    def commit(self, block_hash, txids, votes, accepted) -> Entry:
        return self._append("commit", 0.0, {
            "block": block_hash, "accepted": bool(accepted),
            "txids": list(txids), "votes": list(votes),
        })

    def load(self) -> list[Entry]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [Entry(**json.loads(ln)) for ln in f if ln.strip()]

    def verify(self) -> tuple[bool, str | None]:
        prev = GENESIS
        for i, e in enumerate(self.load()):
            if e.seq != i:
                return False, f"line {i}: seq is {e.seq}, expected {i}"
            if e.prev != prev:
                return False, f"line {i}: broken link to line {i - 1}"
            if e.digest != e.compute():
                return False, f"line {i}: digest mismatch (contents tampered)"
            prev = e.digest
        return True, None

    def txns(self) -> dict[str, dict]:
        """txid -> recorded body, for cross-checking against the chain."""
        return {e.body["txid"]: e.body for e in self.load() if e.kind == "txn"}


def cross_check(journal: Journal, chain) -> list[str]:
    """Compare the two independent records. Empty list means they agree."""
    jr = journal.txns()
    ch = {t.txid: t for b in chain.chain for t in b.txns}
    out = []
    for txid in ch.keys() - jr.keys():
        out.append(f"in chain, not in journal: {txid}")
    for txid in jr.keys() - ch.keys():
        out.append(f"in journal, not in chain: {txid}")
    for txid in jr.keys() & ch.keys():
        j, c = jr[txid], ch[txid]
        for field, cv in (("sender", c.sender), ("recipient", c.recipient),
                          ("amount", c.amount), ("type", c.type.value)):
            if j[field] != cv:
                out.append(f"{txid}: {field} journal={j[field]!r} chain={cv!r}")
    return out
