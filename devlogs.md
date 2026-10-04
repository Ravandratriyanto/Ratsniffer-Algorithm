# Ratsniffer — Dev Logs

A concept **blockchain for fraud / embezzlement / corruption detection**: rule out clean
public spending, surface the corrupt. Core bet — *supervised ML can't catch a scheme it never
saw, but corruption always compromises an invariant* (books don't balance, price out of band,
digits unnatural, physical cash unexplained, money returns to its source). So detection hunts
invariant violations + anomalies first; known-scheme signatures are a fast path on top.

Two parts, clean language seam:
- **`sandbox.html` (JS)** — world generator. Simulates budget flow, plants corruption, exports a labeled `run.json`.
- **`ratsniffer/*.py` (Python)** — detector. Sees only observable fields, rebuilds detection, grades itself vs. hidden labels.

---

## Milestones

### Foundation
- **`chain.py`** — tamper-evident ledger: hash-linked blocks, Merkle root per block, trivial PoW, `verify_chain()`, tamper demo. Editing any committed txn breaks the chain.
- **`ingest.py`** — `run.json` → committed ledger + observable `entities` + held-back `truth` (train/test discipline: detector never sees the answer key).

### Detector stack
- **`gates.py`** — commit-time rules: `price_band` (invoice markup over band), `self_deal` (linked owner), `off_tree_transfer` (kickbacks). A violation is a certificate, not a guess.
- **`analyzer.py`** — `retention_anomaly`: robust peer z-score via median + MAD. Flags nodes holding abnormally much of their inflow vs. peers.
- **`features.py` + `ml.py`** — per-entity feature vector (absolute, not peer-relative) → LogisticRegression `P(corrupt|x)=σ(wᵀx+b)` + IsolationForest novelty. `detect()` flags on **rule OR ML**.
- **`oracle.py`** — the off-chain layer: `attest`/`reconcile` (partial audits reveal real skim + ghost delivery) and `wealth_reconciliation` (honest-investor check).
- **`sniff.py`** — runs the full stack, prints flags + precision/recall vs. truth.

### Headless + adversary (self-play)
- **`world.py`** — Python port of the sandbox sim, so worlds can be generated at scale without the browser.
- **`schemes.py`** — seed bank of real cases (e-KTP, laundering chain, ghost recipient, kickback, embezzlement).
- **`breed.py`** — crossover (splice two real schemes) + motif injection (skim/markup/kickback/shell/ghost/nominee). Turns a few real cases into endless grounded variants.
- **`adversary.py`** — random scheme generator + mutation (the tier-1 fuzzer).
- **`arena.py`** — the self-play loop: generate → detect → score → keep the best evaders → breed → retrain. A genetic algorithm inside a `min–max` game (detector vs. cheater).

### Sandbox features (generator side)
- Generalized **transfers** (send a share of skimmed funds to any node — chain them into kickback/laundering loops).
- **e-KTP case** modeled, then **swapped for a clean government tree** as the default.
- **✦ Scheme** button — auto-builds a scheme step by step (shell → markup → ghost → kickback), animated.
- **Continuous mode** — merged single loop: build a scheme piece → pour money through it → repeat, unbounded. Money always flows while the chart grows.
- **External income (investor)** — per-node outside income with amount / return / linked flag; clean money flows from a **Stock Exchange** fixture, suspicious money from a red shell-source box, frontline nodes cash out to a **Bank** fixture (the off-ramp). Carried into `run.json` export.
- Misc: node-name length cap, free-direction node dragging, `fitView` now frames the true bounding box (incl. fixtures and negative-space boxes).

### Docs
- **`flowcharts.html`** — architecture diagram wiring every file together + a "math in plain English" section (conservation law, geometric series for kickback convergence, hash chain, MAD z-score, logistic curve, precision/recall, minimax). LaTeX via MathJax.

---

## Experiments & findings

- **e-KTP case**: full detector → **100% precision / 100% recall.**
- **Laundering chain** (every node dirty): rules caught Shell firms (price band) + Recipients (self-deal) but **missed Consortium + Money-changers**. Lesson: peer-relative anomaly goes blind when *everyone* is corrupt — no clean baseline, the median itself is dirty.
- **Adversary self-play** (random): ML lifted recall only 82%→85%. The evolutionary loop *discovered on its own* the cheapest evasion — a **bare-skim terminal node** (money in, money kept, no markup/kickback/linked) that's observationally identical to a clean leaf. That's a missing-signal problem, not a training problem.
- **Grounded self-play**: seeding the adversary with *real* cases + breeding produced realistic variants. Adding a **pure-embezzlement seed** lifted held-out recall **71% → 86%** — literal confirmation of "the detector catches what you show it."
- **Oracle wired into the loop**: at **50% audit coverage**, holdout recall 71% → 86%; at **90%**, 71% → **100%**, and the adversary's best evasion collapsed (one round it hid *nothing*). Audit coverage is the single strongest lever — because it injects new truth the ledger can't show. Trade-off: 90% = auditing ~9 of 10 entities (expensive), which is why the oracle is modeled as partial and why audit *allocation* matters.
- **Honest-investor path**: clears independent market income (via Stock Exchange), flags `laundered_wealth` (connected party) and `implausible_returns` (>25%). Being rich isn't the signal; unexplained money tracing to a corrupt source is.

---

## Architecture decisions (for the real-world version)

- **Decentralized + public, never centralized.** A centralized anti-corruption chain is a contradiction. Write-controlled (only treasury posts), read-public (anyone verifies), validated by an adversarial consortium (central bank, audit office, judiciary, civil society) so no one can rewrite history. The real win: **permissionless verification** — anyone re-runs the detector on the public ledger and gets a bit-identical result.
- **Named participants + beneficial ownership.** Everyone with power or a payday is named (vendors, real owners, approving officials, amounts). This isn't just ethics — it's the fuel for `self_deal`/`linked_owner`. The enemy is the anonymous owner / nominee.
- **Private recipients via PPRL, not naive hashing.** Vulnerable end-recipients stay pseudonymous but provably real + eligible. SHA-256 is for exact dedup (keyed, or it's brute-forceable); fuzzy entity-resolution needs **Privacy-Preserving Record Linkage** (Bloom-filter encodings) — *not* a vector DB over hashes (crypto hashes destroy the similarity a vector DB needs). Unmasking only by quorum under due process.
- **Tokenized disbursement (Model B).** The budget is a token minted against the appropriation; every ministry→local transfer is an on-chain hop; gates run as **smart contracts at commit time = enforcement, not just detection**; earmarked/programmable money; keep it digital as deep as possible so cash-out (the dark zone) is late and small.
- **Serverless / dApp fit.** Static front-end (sandbox/flowcharts already are), smart-contract gates on-chain, heavy ML off-chain on independent nodes (re-runnable = trustless), decentralized oracle network for real-world truth. Phones = light clients + crowdsourced reporting + on-device privacy encoding (NPU only matters for deep models / ZK, not the featherweight classical ML).

---

## Honest limitations

- **Our precision/recall is near-circular** — tested against the same simulator that plants the corruption. It proves the pipeline runs, not that it'd catch real-world thieves (unlabeled, messier, adaptive).
- **The oracle is the permanent wall.** You can prove money *moved* on-chain; you cannot prove the school got built or a company isn't a front without real-world verification — which is expensive, gameable, and political.
- **Immutability ≠ honesty.** The chain faithfully preserves a lie entered at the source.
- **Adversaries adapt** — once rules are known, theft moves to what isn't measured (our own adversary showed this).
- **The real blocker is political, not technical** — the people who'd adopt full transparency often benefit from opacity.
- Best framing: **it doesn't catch corruption, it narrows where humans should look** — a prioritization engine for auditors in a digital-funding regime.

---

## Open threads / TODO

- Round-trip an actual **sandbox export (with `externalIncome`) through `sniff.py`** to confirm the JS→Python seam on the new fields.
- Teach the **adversary to generate external income** (honest vs. laundered investors) so the wealth check gets stress-tested in the loop.
- **Tier-3 LLM corruptor** — a model inventing structurally new schemes, not just new parameter combos.
- **External income in the adversary/schemes**, and **model legitimate private income** so the "good investor" case is fully testable via reconciliation.
- **GNN / graph detection** for kickback rings and layering (the natural tool for the graph structure).
- Write the **architecture decisions above into `flowcharts.html`** (or a design doc) so they don't drift.
- Precision tuning: ML got trigger-happy at high training volume (one round dipped to 88%) — threshold / more clean examples.
