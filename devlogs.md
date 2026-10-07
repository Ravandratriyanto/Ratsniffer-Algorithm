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
- **`holdratio_cluster` (net-negative — recorded, not kept as a win).** Same cluster idea on the delivery gap. **Finding: it adds nothing and costs precision.** Full-stack recall stays **83%** (ML's `hold_ratio` feature already catches those), while analyzer-only precision on disguised worlds drops to **64%** (47 FPs); even restricted to leaves it's **71% / 34 FPs** — clean depts and edge leaves drift above the `0.02` floor, which a fixed threshold can't separate from the dirty tail (0.01 vs 0.068 distributions overlap). **Lesson: once a signal is an ML feature, a redundant fixed-threshold hand-rule on the same signal adds noise, not recall.** **Decision: dropped** from `run_analyzer` (function kept on record). Confirmed in the self-play loop — unwiring it lifted rules-only precision **80% → 89%**, rules+oracle **83% → 91%**, steady-state loop precision **79% → 85%**, with holdout/demo recall unchanged (92–100% / 83%) and `sniff.py` still 100/100.

### Honest limit found
Remaining ~17% missed are vendors that rolled **both** markup ≈ 0 **and** capture at the floor → hold ≈ 0.03–0.04, sitting inside the clean distribution. No per-node signal can separate those; it's the genuine floor of what the observable ledger exposes.

### Self-play on the mimicry direction (`arena.py`)
- Seeded disguised schemes into both the population (×2) and the holdout, and **swapped the fitness** from "count missed" to the planned **`value_extracted × fraction_classified_clean`** — so breeding now rewards *profitable disguise*, not loud-and-hidden.
- The new fitness exposes the min-max arms race the old one hid: over 8 rounds the best evader's profit oscillates — driven to **0** in round 3, bred back to **1.17e+11** by round 7. Holdout recall holds 92–100%.

### Strengthening the adversary (making it a real opponent)
- **Mimicry-aware `mutate`.** Rewrote `adversary.mutate` from loud-only operators (capture→0.5, markup→0.8) to disguise-preserving ones: nudge params *within* the thresholds, raise audit, clear `linkedOwner`/transfers, plus structural moves (add a thief leaf, dilute with clean leaves) and a 12% loud tail for diversity. **Finding on wiring:** `mutate` was dead code — `arena` breeds via `breed()`, whose `inject_motif` is loud-only. So the fix only mattered once `breed` was pointed at `mutate` (50/50 with `inject_motif`). Before: the loop literally couldn't evolve *better* disguise, only fall off it. After: the best evader's profit **compounds and no longer collapses** (1.78e+11 → 2.03e+11, never driven to 0), instead of the loud oscillation the earlier note described.
- **Multi-trick disguise.** Each dirty vendor now picks one of **skim / markup / laundered-income**; some clean nodes get *honest* income too. The laundered-income variant (unlinked source, return just under the 25% ceiling) **completely defeats `oracle.wealth_reconciliation` — 0 of 47 caught** — while 54 honest investors are correctly cleared. Worse, the main `detect()` stack has **no external-income feature at all**, so laundered integration is a total blind spot. Same shape as the markup story: a fixed threshold (25%) launderers just park under; honest returns cluster 4–15%, laundered 18–24.8%.
- **Dilution (realism).** `disguised_scheme` defaults → `n_dept=4, n_clean=30, n_dirty=3` (~8% corrupt, not ~40%). This produced the session's sharpest result: the **standalone `demo_mimicry.py` collapsed to 0% recall** (trained only on loud `random_scheme`, never saw disguise; and `markup_cluster`'s per-parent ≥2 assumption breaks when 3 thieves scatter across 4 depts), while the **arena — which retrains on the disguise each round — reached 100%**. A brutal, literal demonstration of *"the detector catches what you show it"* and the learning-loop thesis in one contrast.
- **Cascade (structural disguise).** New `cascade_scheme`: a spine of departments each skimming 1.5–3% and passing the rest down. It defeats every peer/sibling detector by construction — no siblings to cluster (kills `markup_cluster`), every funder on the spine dirty so the median baseline is poisoned (kills `retention_anomaly`), each node inside clean-retention noise. Tuned (spine `share=5`, `fanout=1`) to steal **5.9%** while **97% invisible** to gates+analyzer. In the arena it dragged rules-only recall to **31%** and, unlike every prior disguise, the loop couldn't hold 100% — it kept chasing.

### The cascade's answer: depth-gated `subtree_leakage`
- The one tell a cascade can't hide: **conservation across a subtree** (money in at the top vs. reaching frontline at the bottom). Built `subtree_leakage` to sum `received − paid_out` down a subtree.
- **v1 regressed precision** (`sniff.py` 100% → **60%**): a naive subtree sum implicates the **clean ancestors** of any real skimmer (Consortium's 33% made State budget + Kemendagri's subtrees "leak 100%"), and dead-end non-frontline leaves in `run.json` read as 100% leaked. Lesson: aggregate leakage can *see* theft but can't *attribute* it — localizing to the culprit needs per-node signal (which the cascade erases) or the oracle's true-delivery data (**the real-world wall, again**).
- **Depth-gating fixed it.** Flag a node only if it's internal, keeps **0.5–15%** (excludes big point-skimmers `retention_anomaly` already gets), **and** sits in a **chain of ≥3 consecutive** such tiers (the cascade signature; a one-off retainer or a 2-deep chain doesn't match). Result on the same cascade holdout: **`sniff.py` back to 100/100**, cascade rules-only recall **31% → 69%**, rules-only precision **83% → 92%** (ML stops over-flagging to compensate), cascade full-stack recall **100%** standalone with 1 FP / 160 clean.
- **Residual:** the loop's surviving ~81–88% recall / high evaded profit (~5e+11) is now the **laundered-income** vendors — the vector with zero detector coverage — not the cascade. The arms race surfaced the next real gap on its own.

### Detector stack now
gates → `retention_anomaly` → `markup_cluster` → depth-gated `subtree_leakage` → ML → oracle. `holdratio_cluster` written but **unwired** (net-negative, kept as record).

### Open / next
- **Fill the laundered-income hole** — peer-relative return check (cluster near the 25% line) + an external-income feature in `features.py`; the oracle's `linked` is still a hand-set stub.
- **Commit** — the whole session is uncommitted (adversary, sandbox events, demo, analyzer, arena, breed, flowcharts, `start.bat`).
- Could still push the adversary: deepen the cascade for 10%+, or the audit-blind-spot exploit (hide in the un-audited fraction).
- Still carrying from Oct-4: `TxType.PROCUREMENT` unminted, `transfers_out` `frac > 1`, no tests, no `requirements.txt`.

---

## Session log — 2026-10-07

### Repo state first
Local `main` was 2 commits behind with uncommitted edits to `analyzer.py`, `arena.py`, `ml.py`. Took upstream wholesale (`git reset --hard origin/main`) — now level at **`4379b04`**. The `analyzer.py`/`arena.py` edits were superseded by the upstream versions anyway; the `ml.py` edit had **no upstream counterpart and is gone**, nothing in git ever saw it. Noting it in case something is missed later.

### The eval harness, characterized
`eval.py` (100 lines) shipped in **`4379b04` "Evals and Benchmarks"** — a commit that touched 7 files and **not this log**, which is why there was no record of it. It is the answer to "highest ROI: no tests" from the Oct-4 problem list: not pytest, but a real measurement harness.

Covers, against the project's required-checks list: **label shuffle, single-feature baseline, conditional leak audit, world-seed splits, held-out scheme family, PR-AUC + FPR**. Does *not* cover: the conservation assertion (that lives in the journal work) and generator-seed reproducibility — `dataset(seed=0)` is fixed, so the reported ± is spread across *splits*, not across world seeds. `ml.py:22` does fit IsolationForest on `X[y == 0]` only, so that check passes.

Measured this session — 1755 rows / 90 worlds / 20.0% corrupt:

```
label-shuffle x10    ROC-AUC 0.492 +/- 0.170  [0.238, 0.759]
seed-split x10       ROC-AUC 0.895 +/- 0.011
                     PR-AUC  0.631 +/- 0.027
                     FPR     0.106 +/- 0.021
held-out cascade     ROC-AUC 0.123   PR-AUC 0.272   FPR 0.000
```

No single feature separates — top is `hold_ratio` at 0.792, nothing trips the 0.95 WARN, so the simulator isn't trivially easy. Shuffle mean lands on 0.5: no leak. **But the shuffle spread is the thing to remember** — one draw hit 0.759. A single shuffle run can read as either a leak or clean by luck; only the mean over K means anything, and that matters before anyone quotes one run as evidence.

### The finding: held-out cascade transfer is *inverted*
**ROC-AUC 0.123 with FPR 0.000** is not weak transfer — it is worse than random. Trained on random+disguised, the ML flags **nothing** on cascade and ranks cascade thieves as *cleaner* than clean nodes. Two causes, both measured:

- **The whole family sits below the learned cut.** Training `hold_ratio`: clean mean 0.052, corrupt mean 0.359. Cascade's *maximum* `hold_ratio` across all 420 rows is **0.0207**. Every cascade node, thief included, lands in trained-clean territory.
- **The structural features flip sign across families.** Per-family AUC:

```
feature            random  disguised  cascade
hold_ratio          0.676      0.825    1.000
is_leaf             0.619      0.571    0.062
num_children        0.352      0.429    1.000
received_share      0.373      0.383    0.875
```

  `is_leaf`, `num_children` and `received_share` all invert between the training families and cascade. With `hold_ratio` scaled into irrelevance, those three drive the ranking — in the wrong direction. That is the 0.123.

**The information is fully present.** Within cascade, `hold_ratio` separates *perfectly* by a single cut (corrupt min 0.00779 > clean max 0.00690). Features are absolute, not peer-relative — a deliberate choice recorded back in the `features.py` note — and this is the bill for it. **Lesson: absolute features can't transfer across scheme families whose money scales differ by an order of magnitude; the signal survives, the threshold doesn't.** Next thing to try: within-world normalization of `hold_ratio`.

### And the caution that cuts the other way
`hold_ratio` AUC **1.000** and `num_children` AUC **1.000** *within* cascade is exactly the "one feature separates => too easy" warning. The crosstab says why:

```
cascade              corrupt   clean
  internal              180      30
  leaf                    0     210
```

**Zero corrupt leaves.** In a cascade world "is internal" is very nearly "is corrupt" by construction — `fanout=1` spine, every spine node dirty. So the **cascade full-stack recall 100% standalone** figure below is partly a generator artifact, not detector skill. Read it with an asterisk, and consider giving `cascade_scheme` clean internal nodes so the structure stops being the label.

### Verified
- `sniff.py` unchanged at baseline: 5 validators (quorum 4), canonical chain 2 blocks, journal 6 entries (5 txn) verify OK, cross-check agrees, **precision 100% / recall 100%**. The two upstream commits touched `adversary.py`, `analyzer.py`, `eval.py`, `features.py`, `gates.py`, `world.py` with no regression here.
- All five `eval.py` metric lines, the per-family AUC table, the cascade crosstab, and the `hold_ratio` ceiling/separability figures — read off real runs, not estimated.

### Corrections to earlier entries
- The Oct-5 "Open / next" line **"Commit — the whole session is uncommitted"** is stale: it all landed in `029721b "Adversary Strenghthening"` (Oct 6) + `4379b04 "Evals and Benchmarks"`.
- **"Still no tests"** is now half-true. No pytest and nothing tracked matching `test`, but `eval.py` covers 6 of the 8 required checks — the reason tests were top of the problem list is largely addressed. The remaining gap is unit-level (the recurring-typo class of bug), not evaluation-level.
- Both the mimicry session and the one before it are headed **`## Session log — 2026-10-05`**. The second is really the mimicry session; worth disambiguating if the dates get used for anything.
- The **cascade recall 100%** claim needs the generator-artifact asterisk above.

### Both fixes shipped
Two edits, verified end to end:
- **`features.py`** — new 11th feature **`hold_rank`**: the within-world rank of `hold_ratio`, average-ranked across ties, appended after the absolute vector. Tie-handling is not decoration — dead-end leaves share `hold_ratio` exactly, and ranking them arbitrarily would make the feature depend on dict ordering.
- **`adversary.py`** — `cascade_scheme` tiers now dirty at **p=0.5** instead of universally (`corrupt=dirty`, clean tiers capture ≤ 0.005), so cascade worlds finally contain clean internal nodes. `corrupt=False` is safe to pass: `world.py:149` short-circuits to the capture test, which a clean tier fails.

`eval.py` on the edited tree — every figure matched the scratchpad prediction made before applying:

```
dataset              1755 rows, 253 corrupt (14.4%)   <- was 20.0%; degeneracy gone
label-shuffle x10    ROC-AUC 0.470 +/- 0.195          <- no leak introduced
seed-split x10       ROC-AUC 0.936 +/- 0.009          <- was 0.895
                     PR-AUC  0.686 +/- 0.044          <- was 0.631
                     FPR     0.144 +/- 0.009          <- was 0.106
held-out cascade     ROC 0.982  PR 0.860  FPR 0.130   <- was 0.123 / 0.272 / 0.000
hold_rank alone      AUC 0.820                        <- no WARN
```

`sniff.py` bit-identical to baseline throughout — it imports neither `features` nor `ml`, so the 100/100 was never going to move. Degeneracy confirmed gone: cascade internal nodes **82 corrupt / 128 clean** (was 180/30), `is_leaf` AUC inside cascade 0.062 → 0.189.

Note the generator fix *alone* made every within-distribution number look worse (ROC 0.895 → 0.860, PR 0.631 → 0.521). That is not a regression — it removed a free signal the model had been leaning on. **Numbers from before the generator fix are not comparable to numbers after it.**

### Rank transfers, robust z does not
Tried **median+MAD z-score first and it did nothing** — held-out cascade 0.243 against a 0.245 baseline. Cause: in `random` worlds enough nodes share an identical `hold_ratio` that MAD collapses to ~0, and the z values blow out to **-6.7e+08**. An unbounded normaliser inherits the family's scale problem instead of removing it. Rank is bounded to [0,1] by construction, so it crosses families. **Lesson: the normaliser has to be bounded, not merely robust** — the fixed-threshold lesson again, one level up.

### The caveat that matters more than the fix: generalization is NOT fixed
0.982 held-out came in *above* the 0.936 within-distribution number, which is backwards — out-of-family should be harder. So each family was held out in turn instead of only cascade:

```
held-out random     ROC 0.763  PR 0.601  FPR 0.877
held-out disguised  ROC 0.678  PR 0.131  FPR 0.130
held-out cascade    ROC 0.982  PR 0.860  FPR 0.130
```

**`eval.py:95` hardcodes cascade as the held-out family, and cascade is the easiest of the three** (`hold_rank` alone scores AUC 0.978 inside it). The benchmark has been reporting its most flattering draw. Held-out `random` flags **88% of clean nodes**; held-out `disguised` sits at PR-AUC 0.131. "Generalization solved" would be false.

Why the trick works on cascade and not elsewhere: cascade thieves are consistently the top holders in their own world. The deeper sign conflict is untouched — **all 90 disguised thieves are leaves, all 82 cascade thieves are internal**, so `is_leaf` means opposite things in the two families. Same shape as the original inversion finding, one layer down.

### Bug injection — both caught
- Planted the ground-truth label as a feature → single-feature `AUC 1.000 <-- WARN`, leak audit `100.0% <-- LEAK` on 253 rows, split ROC 1.000. The audits fire.
- Nested the rank pass inside the per-node loop (each node ranked only against nodes seen so far) → held-out cascade ROC 0.982 → 0.919, **PR 0.860 → 0.589**. ROC barely moved and would have passed a casual glance; **PR-AUC is what caught it.** Worth remembering which metric to watch when a change looks fine.

### Open / next
- **Make `eval.py` report all three held-out draws, not just cascade.** The single hardcoded draw is now known to be the flattering one. Changes the benchmark, so it is a decision, not a cleanup.
- **The `is_leaf` sign conflict is the live problem** — disguised thieves all leaves, cascade thieves all internal. Not yet ablated, so "causal" is inferred, not verified.
- **Held-out `random` FPR 0.877** — flagging 88% of clean nodes is the worst number in the project right now, and it was invisible while only cascade was reported.
- **Reproducibility check still missing** — `dataset()` takes a `seed` but `main()` only ever calls it with 0.
- **Re-run `arena.py` / `demo_mimicry.py`** — both call `build_features`, so they picked `hold_rank` up automatically and every number recorded from them is stale. The arena especially: better cross-family generalization is exactly what its fitness is trying to defeat.
- **Add `ext_income_frac` / `max_return` coverage to the stack** — still the laundered-income hole; both active in 397 rows at only 8.3% corrupt-rate, i.e. carrying little signal as built.
- Still carrying: `TxType.PROCUREMENT` unminted, `transfers_out` `frac > 1`, no `requirements.txt`, no unit tests.
