from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

class TxType(str, Enum):
    FUNDING = "funding"
    PROCUREMENT = "procurement"
    KICKBACK = "kickback"
    CASHOUT = "cashout"
    ORACLE = "oracle"
    FLAG = "flag"
@dataclass
class Transaction:
    recipient: str
    amount: float
    sender: Optional[str] = None
    type: TxType = TxType.FUNDING
    good_id: Optional[str] = None
    qty: Optional[float] = None
    unit_price: Optional[float] = None
    ts: float = field(default_factory=time.time)
    oracle_ref: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)
    txid: str = ""

    def _payload(self) -> dict:
        d = asdict(self)
        d.pop("txid")
        d["type"] = self.type.value
        return d

    def hash(self) -> str:
        blob = json.dumps(self._payload(), sort_keys=True,
                          separators=(",", ":"), default=str)
        return _sha(blob)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = TxType(self.type)
        if not self.txid:
            self.txid = self.hash()[:16]


@dataclass
class Block:
    index: int
    txns: list[Transaction]
    prev_hash: str
    ts: float = field(default_factory=time.time)
    nonce: int = 0
    hash: str = ""

    def merkle_root(self) -> str:
        if not self.txns:
            return _sha("")
        layer = [t.hash() for t in self.txns]
        while len(layer) > 1:
            if len(layer) % 2:
                layer.append(layer[-1])
            layer = [_sha(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
        return layer[0]

    def header(self) -> str:
        return json.dumps(
            {"index": self.index, "prev_hash": self.prev_hash, "ts": self.ts,
             "nonce": self.nonce, "merkle": self.merkle_root()},
            sort_keys=True, separators=(",", ":"),
        )

    def compute_hash(self) -> str:
        return _sha(self.header())


class Blockchain:
    def __init__(self, difficulty: int = 3):
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self.pending: list[Transaction] = []
        self._add_genesis()

    @property
    def target(self) -> str:
        return "0" * self.difficulty

    @property
    def last(self) -> Block:
        return self.chain[-1]

    def _seal(self, block: Block) -> None:
        block.nonce = 0
        while not (h := block.compute_hash()).startswith(self.target):
            block.nonce += 1
        block.hash = h

    def _add_genesis(self) -> None:
        g = Block(index=0, txns=[], prev_hash="0" * 64, ts=0.0)
        self._seal(g)
        self.chain.append(g)

    def stage(self, txn: Transaction) -> Transaction:
        self.pending.append(txn)
        return txn

    def mine(self) -> Optional[Block]:
        if not self.pending:
            return None
        block = Block(index=len(self.chain), txns=self.pending, prev_hash=self.last.hash)
        self._seal(block)
        self.chain.append(block)
        self.pending = []
        return block

    def verify_chain(self) -> tuple[bool, Optional[str]]:
        for i, block in enumerate(self.chain):
            if block.compute_hash() != block.hash:
                return False, f"block {i}: hash mismatch (contents tampered)"
            if not block.hash.startswith(self.target):
                return False, f"block {i}: fails proof-of-work"
            if i > 0 and block.prev_hash != self.chain[i - 1].hash:
                return False, f"block {i}: broken link to block {i - 1}"
        return True, None


if __name__ == "__main__":
    bc = Blockchain(difficulty=3)
    bc.stage(Transaction(recipient="treasury", amount=1_000_000_000, type=TxType.FUNDING))
    bc.stage(Transaction(sender="treasury", recipient="edu", amount=530_000_000))
    bc.mine()
    bc.stage(Transaction(sender="ctD", recipient="vnD1", amount=160_000,
                         type=TxType.PROCUREMENT, good_id="school_build",
                         qty=1, unit_price=160_000))
    bc.mine()

    print("blocks:", len(bc.chain))
    print("verify:", bc.verify_chain())          # (True, None)

    bc.chain[1].txns[1].amount = 1               # tamper with a committed payment
    print("after tamper:", bc.verify_chain())    # (False, 'block 1: hash mismatch ...')
