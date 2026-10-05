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

---

## Session log — 2026-10-04

### Shipped this session
- **Money-laundering typologies, full stack.**
  - Pass 1 — `laundering.py`: `round_trip` (money-graph cycles via networkx) and `layering` (pass-through conduit chains). Zero false positives in tests.
  - Pass 2 — `gates.py` two-sided `price_band` (over + under-invoicing) + `structuring` (sub-threshold `chunks`); `oracle.py` `oracle_phantom` (phantom goods). Fields: transfer `chunks`, negative `markup`, node `phantom`.
  - Sandbox: **✦ Scheme** now builds 6 patterns (shell, round-trip, layering, structuring, phantom, under-invoice); panel UI for chunks / negative markup / phantom.
- **Investor / external income.** Sandbox **Stock Exchange** + **Bank** fixtures; clean income flows from the Exchange, dirty from a shell box, frontline cashes out to the Bank. `oracle.wealth_reconciliation` clears honest investors, flags `laundered_wealth` / `implausible_returns`.
- **Decentralization — `consensus.py`.** Multi-validator quorum consensus over `chain.py`. Verified: a lone corrupt node can't rewrite history (its chain invalid, honest quorum canonical); a forged rewrite gets 0 votes. Crosses from "blockchain data structure" to "decentralized ledger with consensus."
- **Consortium wired into `ingest`.** `build_ledger` now commits through a 5-of-N quorum; **external income is a real ledger transaction** (sender = Stock Exchange / shell → recipient), so the Exchange is actually connected. Added fast `entities_and_truth` so `arena` skips consensus per-scheme. Fixed a latent `sniff.py` bug (flagged computed from a partial flag list).
- **Adversary generates the new typologies** (negative markup, phantom, chunks, external income) + `breed.py` motifs; `arena` stress-tests the full stack (100/100 holdout, hid 1–2/round).
- **Sandbox UX:** free camera while running — `userMovedCamera` pauses auto-fit once you pan/zoom/drag, so you can rearrange and zoom out mid-flow. Fit view / Reset layout resume auto-follow.
- **Repo reorg:** `ratsniffer/` (algorithm) + `sandbox/` (generator). Path tweaks: `sniff.py` loads `run.json` script-relative; `start.sh` → `sandbox/sandbox.html`; README run commands. Imports needed no change (Python puts the script dir on the path). Pushed to GitHub as **Ratsniffer-Algorithm**.
- **`README.md`** written (honest framing; tagline: "an algorithm stacked on an algorithmy sandwich").
- **Honest problem audit** done (see below).

### The big realization (next session's main thread)
The current adversary is a **cartoon villain** — it plants obvious dirty nodes (capture 0.5, markup 0.8) that trip every alarm. Real corruption **looks like normal business until you add it up.** Next: a **mimicry adversary** —
1. **Blend-in generator** (`disguised_scheme`): mostly-clean tree, theft hidden *under every threshold* (capture ~0.07 < 0.08, markup < 15% band, no `linkedOwner`, no transfers → evades gates + analyzer). Mark these `corrupt: True` (intent) so they're still *labeled* corrupt.
2. **New fitness** in `arena`: `value_extracted × fraction_classified_clean` → evolve toward *profitable disguise*, not loud-and-hidden.
3. **Expected finding (the point):** the detector will MISS disguised corruption — threshold-per-node detection can't catch "death by a thousand cuts." That motivates **aggregate/pattern detectors** (subtree total leakage, clustering of many small deviations, whole-tree flow shape).
4. **Ground in real KPK case *structures*** (not accusations): social-aid/Bansos skim, infrastructure markup+kickback, state-insurance investment fraud (→ external-income feature), fictitious procurement. Pull actual numbers from KPK's published files; model the *pattern*.

**Started already:** `world.py` now labels by intent (`n.get("corrupt")`) so under-threshold disguised corruption still counts as corrupt — the foundation for the whole mimicry direction. **Resume here:** write `disguised_scheme` in `adversary.py`, then the recall demo, then the new fitness, then an aggregate detector.

### Honest problem list (from the audit — fix order)
- **Highest ROI: no tests.** Zero pytest despite it being a dep — this is why the same typos (`curl`, missing commas) keep reappearing. A dozen tiny tests would end that.
- **Circular evaluation** (detector tested on its own simulator); **oracle reads ground-truth directly** (cheats); **labels share thresholds with detectors** (intent-labeling above starts fixing this).
- Consensus has **no real crypto sigs** (modeled votes) and **no real P2P** (in-process); **arena bypasses the chain**.
- `world.py` ↔ `sandbox.html` duplicate the sim with **no cross-check test** (drift risk); real **browser export round-trip unverified**; `linked` provenance is a hand-set stub.
- Hygiene: no `requirements.txt`; `start.sh` installs unused deps (pandas/scipy); `.pyc` in first commit's history; no input validation; `world.py` has a duplicate `effectiveCapture`/`schemes` line.

---

## Session log — 2026-10-05

### Repo surgery (before any code)
- **Merged the two repos.** Local `Ratsniffer-Blockchain-Algorithm` (9 commits, Sept 8: root `sandbox.html`, `test/engine.test.js`, `DEVLOG.md`) and `Ratsniffer-Algorithm` (Oct 4) had **unrelated histories** — the Oct 4 repo was `git init`'d fresh rather than cloned, so `git pull` refused. Verified the new `sandbox/sandbox.html` contains all the Sept 8 flow-animation work verbatim (`animAt`, `computeAnim`, pour, kickback) plus ~350 lines, i.e. a strict successor. Took the new repo wholesale (`reset --hard`), old head tagged `pre-reset-blockchain-algo` and still on GitHub at the old origin. `origin` repointed to `Ratsniffer-Algorithm`.
- **Casualty:** `test/engine.test.js` (28 checks) is not in the new repo. Recover with `git checkout pre-reset-blockchain-algo -- test/engine.test.js`; it reads the engine out of `sandbox.html`, so it needs repointing at `sandbox/sandbox.html`.
- `__pycache__` untracked + ignored (commit `7a8bb54`). `journal.jsonl` and `.venv/` ignored.

### Shipped this session — the transaction journal
An **independent, append-only record of every movement of money**, separate from the chain.

- **`world.py` emits an event log.** `simulate()` now returns `(S, events)`; `make_run` puts `events` into the run dict so it survives the JSON export. One entry per actual movement, at four sites: `base()` child recursion, `inject()` child recursion, `inject()`'s outflow loop, and the seeds pass — plus the root appropriation. Zero-amount calls are filtered, which correctly drops the cases where `inject` bounces (depth > 8, or dust below `appropriation * 1e-9`).
- **`journal.py`** — JSONL, one line per transaction, each hash-linked to the previous (`prev` → `digest`, sha256 over the canonical form). Verifies standalone: no blocks, no merkle root, no PoW, no consortium. `Journal.record/commit/load/verify/txns` + `cross_check(journal, chain)`.
- **`ingest.build_ledger`** mints one `Transaction` **per event** instead of per node/edge, with `ts=float(seq)` so `txid` is reproducible across runs. Optional `journal=` arg (off by default — `arena` shouldn't pay disk I/O in its hot loop).
- **`sniff.py`** wires it in and prints journal entry count, verify status, and the cross-check verdict.

### The finding that reshaped the design
**A transfer edge is not a transaction — each *firing* is.** `simulate()` is a cascade: the seeds pass fires an edge from parent money, then `inject()` delivers that kickback into the target, which skims it and fires *its own* transfers again, recursing to depth 8. The same edge moves money many times.

Measured: `run.json` plus one return edge (`recipients -> consortium`, rate 0.4) to close a cycle took the log from **6 events to 63**, with `recipients -> consortium` firing **19 times**. The old `ingest` minted *one* txn per edge at amount `n["kickedOut"]` (the node's grand total across all edges and all firings), so a whole cascade collapsed into a single row. That's why the journal is emitted from the sim rather than derived from the model — derivation can't see the cascade.

### Verified
- **Completeness:** `sum(events into X) == S[X]["received"]` exact for every node, on `run.json` and on the cycle variant. Cheapest proof no movement was missed and none invented.
- **Tamper-evidence:** edited amount → `line 2: digest mismatch`; deleted line → `line 2: seq is 3, expected 2`; reopen-and-append resumes `seq`/`prev` correctly.
- **Cross-check** catches all three divergence classes — in chain not journal, in journal not chain, same txid with different fields.
- **`txid` reproducible** across two builds of the same input.
- **No leak:** `events` is local to `simulate()`; arena loop gives identical counts across generations. (First draft had it module-level, which would have accumulated across every generation forever.)
- **No regression:** `sniff.py` still 100% precision / 100% recall, 2 blocks.
- `run.json` regenerated through `make_run` to carry `events` — zero numeric drift against the old file.

### Corrections to earlier entries
- **`disguised_scheme` is already written** (`ratsniffer/adversary.py:44`, 29 lines, under-threshold capture + no `linkedOwner` + no transfers). The Oct 4 "Resume here" pointer is stale — the real blocker is `demo_mimicry.py`, which was typed and never run: `X, y = []. []`, `entities+and_truth`, `random_schemes` (the function is `random_scheme`), `for i ent:`, `truth [i][label]`. Also its eval block sits *inside* the 40-iteration training loop with the `print` outside, so it runs 800 worlds to report one number.
- **`adversary/` at the repo root is a corrupted dead copy** — a pre-Oct-4 snapshot of `ratsniffer/adversary.py`, missing every Oct 4 feature (phantom, `externalIncome`, chunks, negative markup), syntax-broken (`rng=NOne`, `parent=parentshare=`, `rng.choice(ndoes)`), and imported by nothing. Delete it. This is the "same typos keep reappearing" pathology in the problem list, caught in the act.
- `world.py`'s duplicate `effectiveCapture`/`schemes` lines — **fixed**.
- Only 15 of 17 Python files compiled at session start; the two failures were `adversary/adversary.py` and `demo_mimicry.py` above.

### Open threads
- **`TxType.PROCUREMENT` is now unminted.** Events don't carry markup, so nothing produces a procurement txn. Detection is unaffected (`price_band` reads `entities`, not txns), but the FUNDING/PROCUREMENT double-booking decision is now forced rather than deferred: emit a procurement event in `world.py`, or drop the enum member and accept that markup lives on the entity. Note the old code booked *both* at the same sender/recipient/amount — confirmed on `run.json`, `consortium -> vendors` appeared twice at 2,143,355,054,784 — and `unit_price` held a ratio (1.45), not a price.
- **`sandbox.html` must emit the same `events` shape** or the JS→Python seam drifts. Browser exports currently produce no events, so `build_ledger` mints an empty ledger from them. This is the duplicate-sim drift risk in the problem list, now with teeth.
- **`entities_and_truth`'s `transfers_out`** still pairs every transfer with `n["kickedOut"]`, so `off_tree_transfer` can compute `frac > 1` on a multi-transfer node. Independent of the journal; worth fixing on its own.
- `journal.jsonl` is deleted at the start of each `sniff.py` run (appending across runs would stack). Key it per run if history is wanted.
- Still no tests, still no `requirements.txt`. Actual third-party imports across the tree are **networkx, numpy, sklearn** only — `start.sh`'s fallback also installs pandas, scipy, pytest.

## Session log — 2026-10-05

### The thread: the mimicry adversary, start to finish
The Oct-4 "big realization" — the adversary is a cartoon villain — got built out this session. Headline number: **disguised-corruption recall 71% → 77% → 83%**, with `sniff.py` holding **100% / 100%** on the loud schemes throughout (no regression).

### Shipped
- **`disguised_scheme` (`adversary.py`).** Mimicry generator: theft kept under every threshold, labeled `corrupt` by intent so it still counts. First cut planted under-threshold leaves (capture < 0.08, markup < 15%, no `linkedOwner`, no transfers) — verified 5 planted / 0 tripping gates+analyzer, i.e. invisible to the rule layer by construction.
- **Sandbox parity.** ✦ Scheme gained a **`disguised`** pattern. Fixed a real JS→Python **label drift**: the export computed `label` without checking `n.corrupt`, so a browser-exported disguised node came out `clean` — and `ingest` trusts the exported label verbatim. Added `n.corrupt ||` to match `world.py:133`.
- **`demo_mimicry.py` rewritten.** Was committed broken (`X, y = []. []`, `entities+and_truth`, `random_schemes`, eval nested inside the 40-iter training loop). Clean rewrite: train once, evaluate once. Deleted the dead root `adversary/` copy (syntax-broken, imported by nothing).
- **Sandbox event log.** Ported `world.py`'s per-firing `ev()` into the sandbox `simulate()` (`logEv` + 5 log points + export emits `events`). Verified **identical** to `world.py` on a kickback-cycle model — 19 events, same kind breakdown, completeness residual **1.14e-13** both sides. Closes the "browser export mints an empty ledger" drift the Oct-4 session flagged.
- **`flowcharts.html` remade.** Added `consensus.py` + `journal.py` boxes/cards, the "each firing is a transaction" + completeness idea, `markup_cluster` ("death by a thousand cuts") in the analyzer card, `adversary.py` + the mimic framing in self-play, and a new "Disguised skim" tell card. Links/SVG validated.

### Aggregate detectors — what worked and what didn't
- **`markup_cluster` (works).** Flags a cluster (≥2) of sibling children each padding invoices *under* the 15% band — the cluster is the tell, no single child trips. **71% → 77%.** Zero false positives on clean (clean markup is exactly 0, so the band `(1, 1.15)` excludes them).
- **Generator fix — `hold_ratio` was saturated (works).** Root cause of the recall ceiling: disguised leaves were non-frontline dead-ends keeping **100%** of inflow — *identical* to clean leaves, so the `hold_ratio` feature couldn't separate them; markup was the only handle. Made leaves **frontline**: clean deliver ~everything (hold ≈ 0.01), dirty deliver minus the skim (hold ≈ 0.068). That turns the skim into a visible signal. **77% → 83%.**
- **`holdratio_cluster` (net-negative — recorded, not kept as a win).** Same cluster idea on the delivery gap. **Finding: it adds nothing and costs precision.** Full-stack recall stays **83%** (ML's `hold_ratio` feature already catches those), while analyzer-only precision on disguised worlds drops to **64%** (47 FPs); even restricted to leaves it's **71% / 34 FPs** — clean depts and edge leaves drift above the `0.02` floor, which a fixed threshold can't separate from the dirty tail (0.01 vs 0.068 distributions overlap). **Lesson: once a signal is an ML feature, a redundant fixed-threshold hand-rule on the same signal adds noise, not recall.** Decision pending — drop it, or rework peer-relative (per-parent MAD) instead of a global floor.

### Honest limit found
Remaining ~17% missed are vendors that rolled **both** markup ≈ 0 **and** capture at the floor → hold ≈ 0.03–0.04, sitting inside the clean distribution. No per-node signal can separate those; it's the genuine floor of what the observable ledger exposes.

### Open / next
- **Decide `holdratio_cluster`'s fate** (drop vs. peer-relative rework).
- **Commit** — the whole session is uncommitted (adversary, sandbox events, demo, analyzer, flowcharts, `start.bat`).
- Still carrying from Oct-4: `TxType.PROCUREMENT` unminted, `transfers_out` `frac > 1`, no tests, no `requirements.txt`.
