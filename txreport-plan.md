# Transaction Journal — Implementation Plan

An independent, append-only record written every time a transaction takes place.

Not a detector, not a scorecard. A log. Its value is that it is a **second, separate
record of the same events as the blockchain** — if the two ever disagree, something was
altered. That's the whole point of the word "independent."

---

## What it is

One line per transaction, appended the moment the transaction is created, to a plain
JSONL file. Each line is hash-linked to the line before it, so the journal is
tamper-evident **on its own** — it does not depend on the chain's blocks, merkle roots,
PoW, or the consortium being up.

```jsonl
{"seq":0,"txid":"c5a391d6533e7d21","ts":0.0,"type":"funding","sender":"budget","recipient":"kemen","amount":5824480000000.0,"meta":{...},"prev":"000…","digest":"a3f1…"}
{"seq":1,"txid":"e1137da7412835f1","ts":1.0,"type":"funding","sender":"kemen","recipient":"consortium","amount":5331728992000.0,"meta":{...},"prev":"a3f1…","digest":"77bc…"}
```

Readable with `cat`. Verifiable without importing the project.

---

## Where it hooks

This is the one real design decision, and the codebase narrows it down hard:

- **`Blockchain.stage()` — no.** `Consortium.propose()` constructs a `Block` directly and
  never calls `stage()`. It's dead code outside the `chain.py` `__main__` demo. Nothing
  would be recorded.
- **`Validator.commit()` — no.** `propose()` deep-copies the accepted block into all
  N validators, so every transaction would be journalled 5 times.
- **`ingest.build_ledger()` — yes.** It is where transactions are minted, it runs once,
  and it sees each transaction exactly once.

Record at **mint**, not at commit. A transaction that was submitted and then dropped by
consensus is exactly the kind of event an independent record should preserve — if you only
log what the chain accepted, the journal can't tell you anything the chain can't.

So: journal each txn as it's built, then after `cons.propose(...)` returns, append one
`commit` entry naming the block hash and which transactions made it in.

---

## `journal.py`

```python
@dataclass
class Entry:
    seq: int            # position in the journal, monotonic
    kind: str           # "txn" | "commit"
    ts: float
    body: dict          # the transaction payload, or the commit record
    prev: str           # digest of entry seq-1 ("0"*64 for the first)
    digest: str         # sha256 over (seq, kind, ts, body, prev)
```

```python
class Journal:
    def __init__(self, path: str): ...          # opens for append, reads tail for prev/seq
    def record(self, txn: Transaction) -> Entry  # kind="txn"
    def commit(self, block_hash, txids, votes) -> Entry   # kind="commit"
    def verify(self) -> tuple[bool, str | None]  # walks the hash chain
    def load(self) -> list[Entry]                # parse the file back
```

Mirror `chain.py`'s existing conventions so the two agree byte-for-byte on hashing:
reuse `_sha`, and serialize with `json.dumps(..., sort_keys=True, separators=(",", ":"), default=str)`.

`verify()` returns the same `(ok, reason)` shape as `Blockchain.verify_chain()`.

Open in append mode and `flush()` after each write — a journal that loses its tail on a
crash isn't a journal. Don't hold the whole file in memory; `__init__` only needs the last
line to recover `seq` and `prev`.

---

## Wiring it in

`build_ledger` gains an optional journal, off by default so `arena` isn't slowed by disk I/O
in its hot loop:

```python
def build_ledger(run, validators=5, journal=None):
    ...
    for n in run["nodes"]:
        ...
        t = Transaction(...)
        txns.append(t)
        if journal: journal.record(t)
    ok, votes = cons.propose(txns)
    if journal: journal.commit(..., [t.txid for t in txns], votes)
```

`sniff.py` passes `Journal("journal.jsonl")`; `arena.py` passes nothing.

---

## The cross-check (what makes it worth building)

Once both records exist, compare them. This is the payoff, and it's ~20 lines:

```python
def cross_check(journal, canonical_chain) -> list[str]:
    """Every committed txn must appear in the journal with identical fields, and vice versa."""
```

Three discrepancy classes, all worth reporting:

- **in chain, not in journal** — a transaction appeared in a block without ever being recorded
- **in journal, not in chain** — submitted then silently dropped
- **in both, fields differ** — the same txid with a different amount in each record

The first and third are tamper signatures. The second is the one that only an independent
record can see at all.

---

## Two things to know before you start

**1. `txid` is not reproducible.** `Transaction.ts` defaults to `time.time()` and `ts` is
inside the hashed payload, so the same input produces different `txid`s on every run. A
journal is for diffing across runs, so this matters here. Assign a deterministic `ts` in
`build_ledger` (a simple sequence counter is enough) and the problem goes away.

**2. An edge is not a transaction — each *firing* is.** This is the one that reshapes step 1.

`simulate()` is a cascade. `base()` pushes the appropriation down the tree; then the seeds
pass fires each transfer edge; then `inject()` delivers that kickback money into the target,
which skims it and fires *its own* transfers again, recursing until `depth > 8`. The same
edge moves money many times.

Measured on `run.json` with one return edge added (`recipients -> consortium`, rate 0.4) to
close a cycle, `vendors -> recipients` went from 470,429,480,128 to 509,085,033,693 — same
edge, same rate. The difference is vendors re-kicking the 176B it received back as kickback.

`ingest.build_ledger` mints **one** transaction per transfer edge (amount `n["kickedOut"]`,
the node's grand total) and **one** FUNDING transaction per node. So a cascade of N real
movements is recorded as a single row. Accumulating a per-edge total (`t["amount"] += out`)
is closer to right than `kickedOut`, but it still collapses the cascade — and the cascade is
exactly what a journal is supposed to witness.

**So don't derive the journal from the model. Emit it from the sim.** Four sites in
`simulate()` are where money actually moves:

| Site | Movement |
|---|---|
| `base()` child recursion (~line 47) | parent → child, original appropriation |
| `inject()` child recursion (~line 81) | parent → child, kickback money washing down |
| `inject()` outflow loop (~line 91) | transfer edge, fired by kickback money |
| seeds pass (~line 105) | transfer edge, first firing from parent money |

At each, append one event:

```python
events.append({"seq": len(events), "from": src, "to": dst,
               "amount": amt, "kind": "funding" | "transfer", "depth": depth})
```

Have `simulate()` return `(S, events)` — or attach `events` to the run dict in `make_run()`
so it survives the JSON export and the sandbox can emit the same shape. Then
`build_ledger` mints one `Transaction` per event instead of one per node/edge, and the
journal is a direct transcription of something that genuinely happened.

Two consequences worth accepting up front:

- **Transaction count goes up a lot** on runs with cycles. That's correct, not a regression.
- **Per-node sums stay the same.** `sum(events to X) == S[X]["received"]` is a good
  invariant to assert — it's the cheapest proof you captured every movement and no extras.

(Separately: `entities_and_truth`'s `transfers_out` pairs every transfer with `n["kickedOut"]`
too, which is why `off_tree_transfer` can compute `frac > 1` on a multi-transfer node. Worth
fixing on its own merits, independently of the journal.)

---

## Order of work

| # | Task | Notes |
|---|---|---|
| 1 | `simulate()` emits an `events` list at all four movement sites; `ingest` mints one txn per event | the journal's real source |
| 2 | Deterministic `ts` in `build_ledger` | makes `txid` stable across runs |
| 3 | `journal.py` — `Entry`, `record`, `digest` chain | the core, ~60 lines |
| 4 | `verify()` + `load()` | |
| 5 | Hook into `build_ledger` behind an optional arg | |
| 6 | `commit` entries | |
| 7 | `cross_check` against the canonical chain | the payoff |

Steps 1–2 are standalone bug fixes; steps 3–5 are the minimum useful version — a journal you
can `cat` and verify. Stop there if that's all you wanted. 6–7 are what make it a genuine
independent witness rather than a log file.

## Tests worth having

- append three transactions, `verify()` passes
- edit one byte of the middle line, `verify()` names that line
- reopen an existing journal, `seq` and `prev` resume correctly
- `cross_check` on an untampered run returns empty
- drop a txn from the chain, `cross_check` reports "in journal, not in chain"
