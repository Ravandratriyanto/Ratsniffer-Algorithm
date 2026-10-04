# Ratsniffer

> A layered corruption-detection algorithm for public money: flag fiscal flows that
> **violate an invariant** or **look anomalous**, then confirm with off-chain reconciliation.
> An adversarial self-play loop generates and evolves laundering schemes to train and
> stress-test it.
>
> *As a friend put it: an algorithm stacked on an algorithmy sandwich.* 🥪

Ratsniffer is a **concept** — rule out clean spending, surface the corrupt. The core bet:
supervised ML can't catch a scheme it never saw, **but corruption always compromises an
invariant** — books don't balance, a price is out of band, digits aren't natural, physical
cash can't be explained, money loops back to its source. So detection hunts invariant
violations + anomalies first; known-scheme signatures are a fast path on top.

## How it works

Two parts, one clean seam (JS makes the world, Python sniffs it):

- **`sandbox.html`** — an interactive fiscal-flow simulator. Builds a budget tree, plants
  corruption (shells, kickbacks, ghosts, markup, structuring, phantom goods, launderers,
  investors), animates the money, and exports a labeled `run.json`.
- **Python detector** — reads only *observable* fields, rebuilds detection, and grades itself
  against the hidden labels.

**The detector stack** (each layer is a well-known algorithm):

| Layer | File | What it catches | Technique |
|---|---|---|---|
| Rules | `gates.py` | price band (over/under-invoice), self-deal, off-tree, structuring | invariant predicates |
| Anomaly | `analyzer.py` | abnormal retention vs peers | robust MAD z-score |
| Laundering | `laundering.py` | round-trip loops, layering chains | graph cycles / conduit detection |
| Learned | `ml.py` | everything else, including unseen schemes | logistic regression + isolation forest |
| Oracle | `oracle.py` | skim, ghost delivery, phantom goods, fake investors | off-chain reconciliation under an audit budget |

**Self-play** (`schemes.py` → `breed.py` → `adversary.py` → `arena.py`): a seed bank of real
cases is mutated and recombined by a genetic algorithm; fitness = corrupt nodes hidden from
the detector. Detector vs. cheater, a `min–max` game that sharpens both.

**Ledger** (`chain.py` + `consensus.py`): a tamper-evident blockchain committed by a 5-of-N
validator **quorum** — no single node can rewrite history.

## Run it

Requires Python 3.10+ and `pip install numpy scikit-learn networkx`.

```bash
python ratsniffer/sniff.py   # run the full detector on run.json, print precision/recall
python ratsniffer/arena.py   # the adversarial self-play loop
python ratsniffer/chain.py   # blockchain + tamper demo
./start.sh                   # serve the sandbox at http://localhost:8000/sandbox/sandbox.html
```

Layout: **`ratsniffer/`** is the algorithm (Python), **`sandbox/`** is the generator (JS).
`sandbox/flowcharts.html` is a visual map of the whole system with the math in plain English.

## What's original vs. assembled (honest)

Every *primitive* here is textbook — MAD z-scores, logistic regression, isolation forest,
Tarjan cycle detection, Merkle hashing, quorum consensus, a genetic algorithm. The
**contribution is the composition and framing**: invariant-first detection, the layered
stack, and the adversarial self-play that generates its own labeled training data. It's a
detection *system*, not a new core algorithm.

## Honest limitations

- **The scores are near-circular** — tested against the same simulator that plants the
  corruption. It proves the pipeline runs, not that it catches real-world thieves.
- **The oracle is the permanent wall** — you can prove money *moved* on-chain; proving a
  school was built or a company isn't a front needs real-world verification.
- **Immutability ≠ honesty** — the chain faithfully preserves a lie entered at the source.
- Best read as a **prioritization engine for auditors** in a digital-funding regime, not an
  automatic verdict machine.

See `devlogs.md` for the build log and `sandbox/flowcharts.html` for the full picture.
