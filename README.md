# Ratsniffer

> A layered corruption-detection algorithm for public money: flag fiscal flows that
> **violate an invariant** or **look anomalous**, then confirm with off-chain reconciliation.
> An adversarial self-play loop generates and evolves laundering schemes to train and
> stress-test it.
>
> *As a friend put it: an algorithm stacked on an algorithmy sandwich.* 🥪

**New here? Open [`sandbox/flowcharts.html`](sandbox/flowcharts.html) in a browser.** It is a
visual map of the whole system (every file, how the money flows, the math in plain English),
plus a step-by-step flowchart of how one
 office gets flagged or cleared, and the honest coverage
numbers. It is the fastest way to understand the project.

Ratsniffer is a **concept**: rule out clean spending, surface the corrupt. The core bet is that
supervised ML cannot catch a scheme it never saw, **but corruption always compromises an
invariant** (books don't balance, a price is out of band, digits aren't natural, physical cash
can't be explained, money loops back to its source). So detection hunts invariant violations and
anomalies first; known-scheme signatures are a fast path on top.

## How it works

Two parts, one clean seam (JS makes the world, Python sniffs it):

- **`sandbox.html`**: an interactive fiscal-flow simulator. It builds a budget tree, plants
  corruption (shells, kickbacks, ghosts, markup, structuring, phantom goods, launderers,
  investors, cash-out), animates the money, and exports a labeled `run.json`.
- **Python detector**: reads only *observable* fields, rebuilds detection, and grades itself
  against the hidden labels.

**The detector stack** (each layer is a well-known algorithm):

| Layer | File | What it catches | Technique |
|---|---|---|---|
| Rules | `gates.py` | price band, self-deal, off-tree, structuring, dark cash-out | invariant predicates |
| Anomaly | `analyzer.py` | abnormal retention vs peers, clusters | robust MAD z-score |
| Laundering | `laundering.py` | round-trip loops, layering chains | graph cycles / conduit detection |
| Learned | `ml.py` | retention-style theft that transfers across schemes | logistic regression + isolation forest |
| Oracle | `oracle.py` | skim, ghost delivery, phantom goods, fake investors | off-chain reconciliation under an audit budget |

No single layer is complete; the **union** covers most mechanisms. `coverage.py` reports which
layer catches which kind of theft, and where the gaps are.

**Self-play** (`schemes.py`, `breed.py`, `adversary.py`, `arena.py`): a seed bank of real cases
is mutated and recombined by a genetic algorithm; fitness is corrupt nodes hidden from the
detector. Detector vs. cheater, a min-max game that sharpens both.

**Ledger** (`chain.py`, `consensus.py`): a tamper-evident blockchain committed by a 5-of-N
validator **quorum**, so no single node can rewrite history.

## Run it

Requires Python 3.10+.

```bash
pip install -r requirements.txt

python ratsniffer/sniff.py          # full detector on run.json, print precision/recall
python ratsniffer/eval.py           # honest benchmark: held-out families, recall at a false-alarm budget
python ratsniffer/coverage.py       # which layer catches which kind of theft
python ratsniffer/arena.py          # the adversarial self-play loop
python -m pytest ratsniffer/tests   # invariant tests (conservation, no-leakage, feature contract)
./start.sh                          # serve the sandbox + flowcharts at http://localhost:8000/
```

Layout: **`ratsniffer/`** is the algorithm (Python), **`sandbox/`** is the generator (JS).

## What is original vs. assembled (honest)

Every *primitive* here is textbook (MAD z-scores, logistic regression, isolation forest, Tarjan
cycle detection, Merkle hashing, quorum consensus, a genetic algorithm). The **contribution is
the composition and framing**: invariant-first detection, the layered stack, the adversarial
self-play that generates its own labeled training data, and an unusual amount of honesty about
what the thing actually does. It is a detection *system*, not a new core algorithm.

## What it is, and isn't (measured, not claimed)

This is a **fully synthetic prototype**. It has not been validated on real transactions, and the
detector layers were written by the same author as the generators (we grade our own homework).
Everything below is read off a committed script, not estimated:

- **It transfers.** Trained only on synthetic schemes, the stack catches about 99% of corrupt
  nodes in bred variants of real cases it never saw. At a *usable* 10% false-alarm rate that is
  about 64%, clearly above trivial baselines (17% for the top retention feature alone, 11% for
  random scoring).
- **But precision collapses out of distribution.** That recall comes at a ~37% false-alarm rate
  on realistic worlds, because honest offices legitimately hold unspent budget and the detector
  cannot tell that from a small skim. At 1-in-100 prevalence, precision is about 3%.
- **The main open problem**, investigated and logged: the learned retention signal is a recall
  booster, not a precision fix. Two baseline fixes were tried and both failed; the direction is
  to demote retention and let rules and the oracle lead the ranking.

See [`devlogs.md`](devlogs.md) for the full, unflattering build log, and
[`sandbox/flowcharts.html`](sandbox/flowcharts.html) for the complete picture with the real numbers.

## Honest limitations

- **The synthetic scores are near-circular**: tested against the same simulator that plants the
  corruption. They prove the pipeline runs, not that it catches real-world thieves.
- **The oracle is the permanent wall**: you can prove money *moved* on-chain; proving a school was
  built or a company isn't a front needs real-world verification.
- **Immutability is not honesty**: the chain faithfully preserves a lie entered at the source.
- Best read as a **prioritization engine for auditors** in a digital-funding regime, not an
  automatic verdict machine.

## Built with

Architected and directed by the author, who made every design decision and wrote much of the code
by hand. Built with **Claude Code** as an AI pair-programmer that wrote and edited portions under
review. The judgment calls that shaped it (treating retention as a confound, demanding the
sensitivity curve, refusing the flattering number) are the author's.

## License and data

Code is **Apache 2.0** (see `LICENSE`). The file `ratsniffer/data/worldbank_debarred.csv` is World
Bank / MDB debarment data via [OpenSanctions](https://www.opensanctions.org), used under their
open license with attribution.
