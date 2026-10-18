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
- Still carrying: `TxType.PROCUREMENT` unminted, `transfers_out` `frac > 1`, no `requirements.txt`. (**Unit tests: DONE 2026-10-10** — `tests/test_invariants.py`, see the latest entry.)

---

## Session log — 2026-10-08

### The thread: from idealistic claims to a measured curve
Took the ML from "100% precision/recall" framing to a fully measured **catch-rate-vs-false-alarm curve**. Two confirmed levers found (drop sign-flipping features; train on honest worlds), and the detector reframed as a **prioritiser, not a clean classifier**. Nothing about the model got *idealistically better* — the **honesty of the measurement** did, which then exposed how oversold the old numbers were.

### Shipped
- **`eval.py`** — leave-one-family-out now reports **all three families**, not the hardcoded cascade (the flattering draw). Added **`recall@FPR5%/10%`** via `roc_curve` — the honest operating metric. Added **`honest_dataset`** (fully-clean worlds via `disguised_scheme(rng, n_dirty=0)`, with an `assert` that no corrupt label slips in) + a `[honest-only worlds]` FPR line = the real false-alarm rate.
- **`features.py`** — dropped the three structural-position features (`is_leaf`, `received_share`, `num_children`) that **sign-flip across families**; vector 11→8 (`hold_rank` kept, still ranks on index 0 = `hold_ratio`). Dead `children`/`total`/`nkids` removed.
- **`report.py`** — per-entity **ML reasoning** (feature attribution: top-3 by `w·x` off the trained logistic). Then the **deployed fix**: trains on **scheme + 20 honest worlds**, and sets the CORRUPT threshold to **`TAU` = the 10%-false-alarm operating point calibrated on clean worlds**, not an arbitrary 0.5.
- **`sandbox.html`** — **📄 Report overlay** (Transactions / Ground truth / Simulated detector flags), flagged nodes red with plain-English reasoning; **◈ How it works** link to the flowcharts.
- **`flowcharts.html`** — new **eval** card (recall@budget, honest worlds, the curve) and **report** card (reasoning, honest training, calibrated threshold); footer updated. `start.sh` now opens the flowcharts alongside the sandbox.

### Verified — the numbers (all read off real runs this session, single draw seed 0)
Honest held-out picture **after** the features fix:
```
family     ROC     recall@FPR5%  recall@FPR10%
random     0.662     0.000         0.000
disguised  0.752     0.311         0.544
cascade    0.989     0.866         0.988
```
**The finding: ROC massively oversold it.** ROC 0.76 hid recall **0.000 at a usable false-alarm budget** — two of three families catch nothing you can act on. (Before the features fix: random 0.763/0.000, disguised 0.678/0.000, cascade 0.982/1.000.)

### The sign-flip experiment — diagnosis confirmed
Dropping `is_leaf`/`num_children`/`received_share` lifts **disguised recall@FPR10% 0.000 → 0.544** (logistic) / **0.656** (forest). A linear model can't represent a sign flip (leaf = corrupt in one family, innocent in another), so it averages them to mush — that *is* the zero. **The model is the minor lever:** forest with *all* features still gives disguised 0.000, so drop-structural is necessary and the tree is a small bonus. **`random` stays on the floor (≤0.062) in every config** — a different, unsolved problem neither lever touches. **Cascade's perfect score collapses under forest (1.000 → 0.671)** — more evidence it's the generator artifact, since a real signal wouldn't vanish on a model swap.

### The within-family cost of the fix
Seed-split (within-distribution): **ROC 0.936 → 0.891, PR-AUC 0.686 → 0.570, FPR 0.144 → 0.209.** The structural features carried real in-family signal; the trade is cross-family recall bought with within-family precision — and it *hurt* `random` transfer too (ROC 0.763 → 0.662). Not a free win; a genuine judgment call about which family matters.

### The real false-alarm rate
`[honest-only worlds]` (1050 clean nodes, zero fraud): **flagged@0.5 = 27.8%** — *higher* than the 20.9% measured in scheme-worlds. Measuring FPR where thieves exist understated it. An auditor following this into a clean ministry would be sent to >1 in 4 innocent offices.

### The operating curve — there is no quiet-and-thorough point
Threshold calibrated on honest worlds to a false-alarm budget (scheme-only model):
```
FPR 20% → recall 85.0%     FPR 5% → recall 33.6%
FPR 10% → recall 56.6%     FPR 2% → recall 25.7%
```
The 92.9% recall at the default 0.5 was *bought* with 28.7% false alarms. Pull false alarms to a tolerable 5% and you catch barely a third. The detector's real quality is this whole curve.

### Training on honest worlds — a rare clean win
Adding honest worlds to training **lowers FPR and raises recall at the same time** (no trade): FPR **28.7% → 23.7%** (+30 honest) while recall@FPR10% rises **0.699 → 0.743**. The combined curve sits uniformly above scheme-only (+3.5–5.3 pts recall at every budget): FPR10% **56.6% → 61.1%**, FPR5% **33.6% → 37.2%**. The model finally sees legitimate-but-odd *clean* examples and stops flagging them.

### Deployed — the false positive erased
`report.py` on `run.json`, honest-trained at **`TAU` = 0.68**: **Kemendagri** (flagged CORRUPT at p=0.56 earlier this session under threshold 0.5) now reads **p=0.17 → clean**, with all three real thieves still caught (Recipients 0.97, Vendors 0.96, Consortium 0.61 via its rule flag). One world, so a demonstration the fix works *here*, not a generalization claim.

### The reframing (the point of the session)
The detector is a **prioritiser for auditors, not a clean classifier.** Usable band **FPR 10–20% → recall 61–88%** (mixed, buoyed by easy cascade; worse on an unseen family). "100% precision/recall" was the old idealism; the curve is the truth.

### Review round 2 — honesty pass on the page and the report
A reviewer pushed on `flowcharts.html` and `report.py`; fixed, all VERIFIED:
- **Held-out curve now on the page with CIs** (honest-trained, K=5 draws): held-out `disguised` recall@FPR 5/10/20% = **0.49±0.05 / 0.57±0.06 / 0.63±0.05**; `cascade` **0.93±0.04 / 0.99±0.01 / 1.00±0.00** (artifact); **`random` 0.00±0.00 at every budget**. Labelled held-out, not in-family — the page no longer contradicts itself.
- **Held-out honest-world FPR = 0.10±0.01** — calibrate the 10% threshold on one set of clean worlds, measure on another; the budget generalises out of sample. Replaced the single-FP anecdote on the report card.
- **`report.py` `why` now standardised** — `StandardScaler` before the logistic, so `push_j = w_j·(x_j−μ_j)/σ_j` is a genuine log-odds contribution *relative to the average node*, not from a meaningless zero. Reranks reasons: rare features like `off_tree_frac` now surface strongly when active (+17.55 on Vendors).
- **Scorecard card** drops "push both to 100%" for the precision floor `precision = rπ/(rπ + f(1−π))` and `precision@k` as the honest headline.
- **Sign-flip reframed** as a generator confound ("our generators leaked structure into the labels"), not an insight about real fraud.
- Shuffle card now says *train on shuffled labels, test on true, averaged*; consensus says *five simulated validators in one process* (no overclaim); ledger buckets each defined (now backed by a `make_run` conservation assert — see the off-ramp work below).

### Modelling the off-ramp — funding→cash, made detectable
The one place "follow the money" stopped: the cash-out / dark zone. The Bank was visual-only; `delivered`/`retained`/`diverted` were identical ledger entries that just stopped. Built it out end to end:
- **Sim** (`world.py` + `sandbox.html` parity): every node emits a `cashout` event to the Bank, `cashedOut = delivered + diverted(net)` (authorised delivery + skim withdrawn as cash). Added the **project's first conservation assert** in `make_run` (`received == diverted+retained+down+delivered+kickedOut`); holds across 40 generated worlds. Sandbox mirrors it (JS `cashedOut`, `cashout` events, a "Cashed out" footer stat) — JS↔Python parity kept.
- **Ledger** (`chain.py`/`ingest.py`): `TxType.CASHOUT` minted per event; `cashed_out`/`delivered` exposed as observable fields.
- **Detector** (`gates.py` `dark_cashout`): flags `(cashed_out − delivered)/received > 0.08` — cash leaving the rails beyond authorised delivery.

**Verified:** `dark_cashout` over 120 worlds (all three families) = **100% precision, 26% recall, 0 false positives** (92 caught / 0 FP). On `run.json` (regenerated from `schemes.ektp()` via `make_run`, **0.0 drift** on existing fields): fires on Recipients 53%, Consortium 23%, Vendors 22%; `sniff.py` still **100/100**; journal 6→11 entries; cross-check agrees.

**The feature that didn't survive measurement:** `cashout_frac` as an ML feature was a **family-dependent confound** — single-feature AUC **0.376** (dominated by legitimate frontline delivery, not skim), and it tanked held-out transfer (disguised recall@FPR10% 0.544→**0.089**, cascade 0.988→**0.000**). Same disease as `is_leaf`. Measured, rejected, **reverted** — the cash-out signal belongs in the gate (which strips the delivery component), not the model. The "measure before you ship" loop caught it.

**Honest limit:** `dark_cashout` is high-precision *partial* (26% recall) — it catches only thieves who withdraw skim as cash beyond authorised delivery, by construction. And `cashedOut = delivered + diverted` is the clean first model with **no legitimate operational-cash noise**, so it's somewhat idealised (though the 0.376 feature AUC shows it is not a trivial label leak). The *probabilistic* off-ramp model (scope option 4) was not built.

### The `random`-family floor — lifted (generator confound, not a smarter detector)
The session's last big open problem: held-out `random` stuck at **0.00 recall at every false-alarm budget**, untouched by the sign-flip and honest-training levers. Diagnosed it (scratch `randdiag.py`), and it was the sign-flip disease one level deeper — **not** signal-absence:
- Within random the signal *is* present (per-feature AUC `hold_rank 0.69`, `hold_ratio 0.68`, `off_tree_frac 0.68`).
- But the model (trained on disguised+cascade) scored random's **clean** nodes at **0.563** — over-flagging everything, so any usable-FPR threshold excluded the corrupt → 0 recall.
- Cause: **`random_scheme`'s clean leaves were non-frontline dead-ends that *retain* their inflow**, while `disguised`/`cascade` clean leaves are `frontline` and *deliver* it. So `hold_ratio` meant "corrupt" in two families and "normal dead-end" in the third — a generator confound, the `is_leaf` story again.

**Fix (`adversary.py`):** mark `random_scheme`'s leaf nodes `frontline` (deliver, `retain=0`) — exactly the fix applied to disguised earlier in the project. Clean leaves now look alike across all three families.

**Measured (K=5, honest-trained):** random recall@FPR5% **0.00 → 0.65±0.14**, @FPR10% **0.00 → 0.75±0.10**; the model's score on random's clean nodes dropped **0.563 → 0.308**. Bonus: within-distribution seed-split ROC **0.891 → 0.935**. No leak introduced (label-shuffle 0.47, no single-feature WARN, honest FPR still 0.10±0.01).

**Honest framing:** this is a **generator-consistency fix, not a detector improvement** — we made the simulator's clean nodes behave realistically (spend, not hoard), removing a confound we had planted. The benchmark got fairer; the model didn't get smarter. **All prior random-world numbers are now stale** (the generator changed), and random's CI is wide (±0.14) — directional, not precise.

### Coverage matrix + the bred false-alarm finding (`coverage.py`)
Replaced the single held-out recall number with a **coverage matrix** — mechanism × layer (rules / ML / oracle / combined), recall of corrupt nodes. Built `coverage.py` (committed).

**Synthetic single-mechanism worlds** (recall): the union is complete *except mimicry* —
```
                 rules   ML   oracle  combined
retention        100    100    100      100
markup           100     56    100      100
self-deal        100     92    100      100
phantom goods      0      0    100      100
external income    0    100    100      100
pass-through ring 100    100     28      100
disguised (mimic)  0     69      0       69
```
Each layer owns a column of blind spots and the others cover them — rules = structural tells, ML = relative retention, oracle = no-on-ledger-trace (phantom). The only uncovered row is **disguised/mimicry (69%)**, theft tuned under every threshold.

**External validity (the real test of same-author bias):** the ML, trained only on the 3 synthetic families, was run against **replayed real cases** (`schemes.py`: ektp/launder/ghost/kickback/embezzle) and **40 bred variants** (`breed.py` crossover/motif of those). Recall: real cases 100% each (ghost oracle-only, as expected); **bred x40: rules 90 / ML 91 / oracle 98 / combined 99%**. Recall genuinely transfers to schemes it never saw.

**The finding that reframes it — bred false-alarm rate:** the 99% recall comes at a **37% false-alarm rate** on bred/real worlds (rules 14, ML 28, oracle 2, combined 37). The ML was calibrated to 10% FPR on *synthetic honest worlds whose clean nodes deliver* (hold≈0); real/bred worlds have clean nodes that **retain** (embezzle's unit keeps 90%, Kemendagri holds), which look identical to small skimmers → over-flagged. **Recall transfers; calibration does not.** This is the direct cost of the earlier "fix random by making clean leaves deliver" — the retention-heavy honest world isn't an edge case, it's where precision lives or dies (the reviewer's point #3, now measured). The oracle is the only layer that stays clean out of distribution (2% FPR).

**The honest headline (eval card rewritten around it):** *the learned component finds corruption even in unseen schemes (99% recall on bred real-case variants), but on realistic worlds where honest offices hold budget it false-flags ~37% of them — out-of-distribution precision collapse, because legitimate retention and skim are indistinguishable without a delivering baseline.*

### Honest limits / still open
- **Single draws, seed 0** — directions solid (sign-flip reproduces across `eval` and the scratch experiment), magnitudes want K-averaging before quoting.
- The honest-training fix is wired into **`report.py` only**; `eval.py`'s `dataset()` left pure on purpose so cross-family evaluation isn't polluted.
- **`random`-family floor — LIFTED** (0.00 → 0.65/0.75 recall@FPR5/10%) via a generator-consistency fix; see the subsection above.
- **`off_tree_frac` is a near-answer-key** (active 30 rows, 96.7% corrupt) — below the 98% LEAK threshold but watch it.
- **DONE this session — the report's `why` is now standardised** (`report.py` scales features before the logistic), so `push_j = w_j·(x_j−μ_j)/σ_j` is a log-odds contribution relative to the average node; the earlier raw-`w·x`/`x=0` baseline is fixed.
- **Reviewer's flowchart math/wording fixes — DONE** (`flowcharts.html`): structuring `$1M → $1.08M` (12×$90k); minimax now `E − λD` (value extracted minus detection penalty, i.e. profitable disguise); robust-z now `(x − median)/(1.4826·MAD)`; ledger buckets made disjoint (`skim kept + retained + sent down + delivered + kicked back`, so kickback isn't double-counted inside skim); layering card gained the honest-pass-through caveat ("flags structure, not intent"); quorum stated as `N=5, quorum=4, tolerates 1 faulty`; gates card no longer says "cheating always breaks a rule" — now distinguishes loud (breaks a rule) from disguised (breaks an aggregate invariant), resolving the contradiction with the mimic card.
- **Still open from the review:** collinear reasons not yet grouped (`hold_ratio`/`hold_rank` can both appear as "one fact"); IsolationForest novelty flags still have no surrogate explanation (now *stated* on the page, not built); `precision@k` is framed on the page but not computed anywhere yet.
- **Off-ramp follow-ups (from this session's cash-out work):**
  - `cashedOut = delivered + diverted` has **no legitimate operational-cash noise** — real clean nodes withdraw cash for payroll/operations too, so the current model makes cash-out cleaner than reality. Adding that noise is the honest next step (and would test whether `dark_cashout` survives it).
  - **`dark_cashout`'s 26% recall is a hard ceiling by construction** — it only sees skim *withdrawn as cash beyond authorised delivery*; thieves who park skim as a digital balance or stay under the 8% tol are invisible to it.
  - The **probabilistic off-ramp** (scope option 4 — a per-path risk score for funds going dark) was explicitly **not built**; only the deterministic event + gate.
  - `run.json` is now regenerated from `schemes.ektp()` via `make_run` (0.0 drift), so the demo carries cash-out — but it is still **one hand-built world**; real quality remains the eval curve.
- **The new frontier (floor now lifted):** add legitimate operational-cash noise to the off-ramp (does `dark_cashout` survive it?); and the uncomfortable meta-question — most gains this session came from *fixing generator confounds* (`is_leaf`, then random's hoarding leaves), so **how much of the held-out curve is real detection vs. the simulator no longer differing in convenient ways?** Stress-testing that is the real next step.
- **DONE — `eval.py` now K-averages in the harness.** `held_out_ci(K=5)` runs honest-trained leave-one-family-out + the out-of-sample honest FPR over 5 world draws and prints mean±std; the committed harness reproduces the current CIs (random 0.65±0.14 / 0.75±0.10, disguised 0.48±0.07 / 0.62±0.06, cascade 0.98±0.02 / 0.99±0.01, honest FPR 0.10±0.01) — no more scratch scripts.
- `off_tree_frac` is still a near-answer-key (active 30 rows, 96.7% corrupt) — below the 98% LEAK threshold but watch it.

---

## Session log — 2026-10-10

### Reality check against external data (first ground truth from outside the loop)
The project self-grades — we author the schemes, the detectors, and the labels (red team and blue team both on our payroll). Pulled the first *unauthored* data to sanity-check the premise: the **World Bank debarred-firms list** (OpenSanctions, `data/worldbank_debarred.csv`, 1,394 legal entities, confirmed MDB fraud/corruption sanctions).

**What it is / isn't.** Real *labels* (confirmed-corrupt firms), **no features** — names, countries, sanction reasons only; no bids, prices, amounts, or flow. So it **cannot serve as test data** (no recall measurable on it). Its value is **typology** — what kinds of corruption real enforcement catches.

**The reasons, read with discipline:** **578 of 1,420 entries are "cross-debarment"** (type hidden — imported from ADB/EBRD/IDB/AfDB), and the top-12 reasons cover only 1,074, leaving **346 in a long tail (136 distinct strings)**. So **percentages are not quoted** and the readable mix is a lower bound. What *is* readable skews to procurement-process misconduct: the Bank's fraud/corruption/collusion guideline citations (~300), "controlled affiliate of a sanctioned entity" / shell structures (240), explicit fraudulent practice (37). Shells/affiliates (240) + phantom-style fraud map to things we already model; collusion/bid-rigging does not.

**The finding (reworded, not overstated):**
> Real MDB debarments are dominated by procurement-process misconduct (bidding fraud, collusion, shell/affiliate networks), not budget-flow retention. Our retention signal transfers across synthetic families but has no counterpart in debarment reasons. **Enforcement data is not prevalence data** — these lists show what investigators can prove from documents and bids, not what occurs; quiet budget leakage is under-represented by *selection*, not necessarily rare (public-expenditure-tracking surveys exist precisely because funds leak between levels of government). Next step: add a procurement-integrity module alongside the leakage module.

**Caveats recorded (so nobody re-overstates this later):**
- "~0% of real corruption" would be wrong — it's ~0% of *this list's readable reasons*, from a selection-biased enforcement source.
- **Comparison-set caveat:** the Bank sanctions firms in *Bank-financed* projects; national-treasury embezzlement is prosecuted by national agencies and wouldn't appear here. So this says what to *add*, not that the retention module is invalid.
- "Zero individuals" is a property of the **firm-list** source we pulled, not a claim about individuals.
- The earlier "single-bidding was opentender's #1 indicator" line came from a web-search summary — **unconfirmed against a primary source, so it is not asserted here.**

**What the data can / can't do:** *can* set the typology mix (which families to simulate) and justify new modules; *cannot* be test data (no bids/prices/graph → no recall).

### Next: a procurement-integrity module (planned, not built)
A new scheme family with its own held-out test; **expect the retention feature to score near chance there — that is the finding, not a failure.** Keep the leakage module (legitimate second domain; arena/eval/honesty checks all transfer). Signals to simulate: single-bidding rate; bid dispersion `CV = σ/μ` (rigged bids cluster too tightly or space too evenly); winner premium `bid_win/estimate` clustered just under the ceiling; firm rotation (a small set taking turns winning); **shell networks** (shared address/director/owner — graph-shaped, where a GNN fits); short submission windows / last-minute spec changes.

### Data access reality
- `opentender.eu` per-country dumps carry bid-level data **plus** DIGIWHIST integrity indicators, but the site **403s automated fetch** — needs a manual browser download (the per-country "Data" button). Human-in-the-loop only.
- `data.open-contracting.org` Indonesia OCDS mirror is fetchable but has **bidder count / method unpopulated** (no bid-level signal) and is 211 MB — not usable for this.
- World Bank debarred list: fetchable by script (done), but labels-only.
- To check for downloadable/licensed bid-level data: Indonesian **LPSE/SPSE** portals, EU **TED** bulk open data (EU-wide, large), opentender per-country dumps.

### Procurement-integrity module — scaffolded, honesty check caught it too easy
Built `procurement.py`: a **new domain** (tenders with bids, not a budget tree). Clean tenders have 3–6 dispersed bids; rigged ones are single-bid or cover-bid collusion (winner just under estimate, losers clustered 0–3% above). Features: `single_bid`, `bid_cv` (σ/μ), `winner_premium` (winner/estimate), `n_bidders`. **Reuses `eval.py`'s honesty harness** (`split_by_world`, `recall_at_fpr`, `ms`, `fit_score`, label-shuffle) — so the discipline transfers to the new domain for free, which was the point.

**Result — not a win, a caught artifact:** `winner_premium` single-feature **AUC 1.000** (WARN), `bid_cv` a perfect *inverse* separator (0.001); held-out ROC/recall **1.000**. The rigged and clean distributions don't overlap, so the 100% is a **generator artifact, not detection** — exactly the "too easy simulator" failure the single-feature check is built to catch, now firing on contact in the new domain. label-shuffle 0.566 ± 0.321 (wild variance on the small buyer splits). **The genuine win is that the honesty machinery transferred and flagged the easiness instantly** — no real recall number is claimed.

**Next on this module:** harden the generator so rigged/clean *overlap* (collusion that doesn't price the winner so obviously under estimate; clean tenders that sometimes cluster) before any held-out number means anything. Add rotation and shell-network (shared address/owner) as graph features. And the standing caveat holds: this is still synthetic — both teams authored by us on a new battlefield; real validation needs the manual opentender download.

### The open problem, investigated — three experiments, mostly negative (`openproblem.py`)
The 37% false-alarm collapse got three planned experiments. All VERIFIED off a real run; the headline is that the problem is **worse** than a tunable threshold.

**1. Sensitivity curve — the 37% is an assumption, not a constant.** A parameterized `realistic_honest(p_hold)` generator (a share `p_hold` of clean offices legitimately retain 15–40% as reserves; the rest deliver). Union FPR vs `p_hold`:
```
p_hold:  0.0   0.1   0.2   0.3   0.5
FPR:     10%   14%   18%   26%   44%
```
The "37%" ≈ `p_hold` 0.4. The false-alarm rate is a steep function of how retention-heavy you assume reality is — so it should be reported as a curve, not a number.

**2. Peer baselines by function — FAILED.** Ranked `hold_ratio` within function (hospital/school/ministry; functions assigned orthogonally to the corrupt label, so no leak). FPR got *worse* at every `p_hold` (10/16/23/32/50% vs global 10/14/18/26/44%), recall unchanged (0.90). **Why:** ranking *within* a group of all-retainers still spreads them 0–1, so the top reservers still rank high and still get flagged. Within-function *ranking* is the wrong fix; the right one is deviation from a function's *expected* hold (per-function baseline / z-score), which this rules in by ruling the ranking out.

**3. Oracle with a budget (precision@k) — the alarming one.** Realistic framing: ML ranks, oracle confirms the top-`k`. On a mixed pool (15% corrupt = bred criminals + realistic honest reservers):
```
k=1%  precision 0.22   k=5%  0.04   k=10%  0.02      recall@k ≈ 0.01 everywhere
```
**Honest reservers outrank the actual criminals** — because many real/bred thieves steal via markup/collusion with *low* retention, while legitimate reservers hold 15–40%. So the retention-dominated ML ranks the wrong people first; an inspection budget on its top-`k` catches ~1% of corruption — *worse than random*. The "ML ranks, oracle confirms" deployment story **does not work with a retention-dominated ranker.** (Caveat: the exact precision@k depends on the honest/corrupt mix chosen, `p_hold`=0.3; the *direction* — reservers above criminals — is the robust result.)

**What the three establish together:** the open problem isn't a tunable FPR. The ML's one transferable signal (relative retention) is, on realistic mixed populations, **actively anti-correlated with catching non-retention crime** — which is most real crime (the debarment finding). The viable directions are now narrowed: (a) a function-specific *expected-hold* baseline (deviation, not rank), or (b) demote retention and let rules/oracle lead the ranking. A bigger recall number is not the goal; fixing the misranking is.

### Fix attempt: expected-hold baseline — also failed (`openproblem.py`)
Direction (a) tried: flag **deviation from a function's expected hold** (robust z within function, `(hold − median_fn)/MAD_fn`) instead of ranking — a legit ministry at its function's norm scores z≈0, a thief above its peers flags. Added as a third variant. VERIFIED off a real run:
```
                bred recall   honest FPR (p_hold 0 → 0.5)
global rank        0.91       10 → 44%
function rank      0.90       10 → 50%
expected-hold z    0.99       10 → 51%
```
precision@k unchanged (0.22 / 0.04 / 0.02 at k=1/5/10%). **It raised recall (0.91 → 0.99) but did not cut the false-alarm curve (same/worse than global) and did not fix the misranking.** Cause: the **MAD→0 blowup** the Oct-7 "rank transfers, robust-z does not" note already warned about — at low holding every honest node holds ~0, MAD collapses to the `1e-6` floor, the z explodes into clipped noise (±8), and `tau` gets calibrated on that noise.

**So both retention-baseline fixes (function-rank, function-z) fail on precision.** Retention is a *recall* booster, not a precision fix — no baseline rescues it. This settles the open problem toward **direction (b): demote retention, let rules and the oracle lead the ranking.** The `openproblem.py` three-way comparison is the committed record.

### Tests — the first real unit net (`tests/test_invariants.py`)
The oldest item on the problem list (Oct-4: "highest ROI: no tests") is finally closed — not the measurement harness (`eval.py` did that), but **pytest unit tests** that catch the recurring-typo / silent-drift class of bug that plagued every session. Seven tests, `7 passed in ~1.2s`:
- **conservation** (`received == diverted+retained+down+delivered+kickedOut`) and **cash-out identity** (`cashedOut == delivered+diverted`), across all three families;
- **feature contract** (`len(vector) == len(FEATURES_NAMES)`) — the exact silent mismatch that bit `features.py` edits repeatedly;
- **no leakage** (entities expose no `label`/`trueDelivered`/`schemes`/`corrupt`/`diverted`);
- **reproducibility** (`dataset(seed=0)` identical across calls);
- **label-shuffle ≈ chance** (shuffled-label AUC mean < 0.70);
- **no single feature separates** (every single-feature AUC < 0.98 — simulator not trivially easy).

**Proven to have teeth** (CLAUDE.md "break your own work"): planted a stray feature (vector 8→9), ran → `FAILED … assert 9 == 8`; reverted → `7 passed`. So the drift bug that was silent all session now fails loudly in ~1 second — the maintainability keystone for making this open-sourceable. **Honest coverage gap:** this is the core invariant set, not all 8 CLAUDE.md checks (no seed-split-spread, held-out-family, or IsolationForest-fit-on-honest-only yet); and a **`requirements.txt`** now pins the real deps (`numpy`, `networkx`, `scikit-learn`, `pytest`), so a fresh `./start.sh` installs them (its `if [ -f requirements.txt ]` branch picks it up) — closing the other long-standing "no requirements.txt" item.

---

## Session log — 2026-10-14

### First real, unauthored data — opentender Cyprus (the milestone, honestly bounded)
The whole project self-grades; this is the first time its logic touched data neither of us wrote. Pulled **opentender.eu** (DIGIWHIST) Cyprus: **12,699 real public tenders**, as NDJSON with the facts (procedure, bids under `lots[].bids`, `estimatedPrice`/`finalPrice`) **plus DIGIWHIST's own integrity indicators** baked in. Data is **CC BY-NC-SA (non-commercial)** → gitignored (`ratsniffer/data/*.ndjson`, `/*.zip`); only results go in the repo, never the data.

**The comparison (concordance, not validation):** computed our procurement invariants (single-bid from `len(lots[].bids)`, non-open procedure, winner-premium `final/estimated ≥ 0.98`) on 3,824 awarded tenders, and checked whether they flag the same contracts DIGIWHIST rates low-integrity.
```
non-open procedure:      33.6%
winner premium median:   0.92   (37.5% win at >=98% of estimate)
opentender integrity:    median 50/100
CONCORDANCE: our combined red-flag vs opentender low-integrity  ->  AUC = 0.803
  (our-flag mean 1.85 on low-integrity vs 1.04 on high)
```
So our hand-written invariants agree with an **independent, established methodology** on real contracts at **AUC 0.80** — the first evidence the detector's logic recognizes the same risky contracts the European experts do, outside the simulator. The honest milestone.

**The honest caveats, logged so nobody oversells this:**
- **Concordance ≠ validation.** Opentender's indicators are themselves *heuristics*, not confirmed corruption. There is **no "corrupt" label** in the data — there never is, for anyone. We agree with another flag system; neither caught a proven thief.
- **Partial circularity** inflates 0.80: opentender's integrity *includes* single-bid and procedure-type — the same concepts in our flag. The one independent signal is winner-premium.
- **The single-bid field is a data artifact.** 80.8% of awarded tenders show "1 bid" because Cyprus logs only the *winner*; opentender's own `INTEGRITY_SINGLE_BID` correctly reads `INSUFFICIENT_DATA` and abstains where our naive rule fires. On real files, a rule is only as good as the fields the government filled in — and opentender is more honest here than our rule was.
- Tests the **procurement side only** (`procurement.py` logic, via hand rules — the ML sat this out, no money-flow in procurement data). The budget-leakage detector still has no real-world input.

### No ground-truth anchor exists in what we can get
- **Debarred-firm cross-reference: 0 hits.** Matched all 1,394 World Bank debarred firms against 4,461 Cyprus suppliers — **zero** exact matches (the "near" matches were coincidental shared words like "waste management"). Reason: WB debarments are construction firms on *WB-financed* projects in developing countries; Cyprus is EU, non-WB-funded — **non-overlapping universes**. So no Cyprus tender can be tied to a confirmed-bad firm here.
- **EU exclusion registers are mostly private.** Italy's ANAC *Casellario* Section B (the exclusion data) is **reserved to contracting authorities**, not public — and that's the common EU pattern (OECD/SIGMA). So a clean "public debarment register + opentender coverage" join is scarce; the ground-truth wall is partly **policy**, not just download friction. Best candidate to verify for a register-join is Slovakia; the reliable route is hand-linking **adjudicated** OLAF/EPPO/court cases to their opentender records (manual, but real labels).

### Next
- **Generalization re-test:** run the same concordance check on an opentender **Italy** year-slice (not the 3.5 GB all-time dump) — does the ~0.80 agreement with DIGIWHIST hold in a second, larger country, or was it Cyprus-specific?
- De-circularize: re-run concordance using **only winner-premium** (drop the shared single-bid/procedure concepts) to isolate the genuinely independent agreement.
- The only road to real labels remains hand-linking adjudicated cases; no bulk download delivers it.

---

## Session log — 2026-10-15

### Italy extracted + characterized (field population only — no AUC computed yet)
Extracted `data-it-ndjson.zip` into `ratsniffer/data/` (gitignored by the existing `*.ndjson` rule): **21 years, 2002–2024, 30 GB** — ~200× Cyprus, so the concordance script must **stream line-by-line and sample years**, not load. All figures below are VERIFIED off sampled scans (2015 ~30–80k lines, 2007 50k), not full-file.

Field population (Italy ≠ Cyprus):
```
                 estimatedPrice   finalPrice(raw)   digiwhistPrice
Cyprus 2015          43.6%            88.2%             97.9%
Italy  2015         100.0%             0.0%            100.0%
```
- **`finalPrice` is dead in Italy (0%, tender + lot).** `estimatedPrice` and `digiwhistPrice` are both 100%.
- Awarded (has ≥1 bid) ~55% of records; **pre-2008 is notice-only (0 bids)** → use **2015+**.
- single-bid share **74.3%** (Cyprus 80.8%) — same "logs only the winner" artifact; DIGIWHIST's own `INTEGRITY_SINGLE_BID` is CALCULATED on only 74% and abstains elsewhere.
- **`indicators` present on 99.9%** of awarded (I first missed it — my schema dump was on a notice-only 2007 record with none). Richer than Cyprus: SINGLE_BID, PROCEDURE_TYPE, ADVERTISEMENT/DECISION_PERIOD, SUPPLIER_SHARE, BENFORDS_LAW, DISTINCT_MARKET, MULTIPLE_VALID_BIDS + transparency fields. **The concordance baseline is intact.**

### The finding: Italy's award price is unverifiable from within Italy (the `digiwhistPrice` provenance problem)
Winner-premium is the **one independent signal** in the concordance (single-bid + procedure-type are shared with — thus circular to — opentender's integrity score). In Cyprus it came from the raw government `finalPrice`. Italy has **no raw `finalPrice`**, so winner-premium must be reconstructed from **`digiwhistPrice/estimatedPrice`** — and `digiwhistPrice` is DIGIWHIST's *computed* field.
- **VERIFIED (Cyprus):** where both raw `finalPrice` and `digiwhistPrice` exist, **`digiwhistPrice == finalPrice` 100%** (n=247). So in Cyprus `digiwhistPrice` is a cleaned mirror of the reported final price, and the raw field was there to *prove* it.
- **INFERRED, not verifiable in Italy:** that Italy's `digiwhistPrice` is likewise the awarded price. The pattern is *consistent* (differs from estimate on 66.2% of awarded, median ratio 0.962, winner-premium computable+sane [0.3–1.3] on 98.1%, 46% ≥0.98) — but equally consistent with it being a DIGIWHIST model/cleaned estimate, in which case every Italy winner-premium number is meaningless.
- **Gate — attempted, and it CANNOT be done from within the Italy data (VERIFIED 2026-10-15).** Two routes both dead: (1) `publications` carry **no inline prices** — only source pointers (`formType`, a `machineReadableUrl` to ANAC *bulk* datasets like `.../dataset/agg`), so there is no per-tender value to check against; (2) raw `finalPrice` is **absent in all 286,150 tenders across all 25 Italy files** (tender- and lot-level), so the Cyprus-style `digi==final` confirmation has nothing to verify against. The only positive evidence is circumstantial: the award-vs-estimate skew (62% under / 4.8% over / 33% exactly equal — award outcomes look like this, a re-cleaned estimate would not) plus the Cyprus precedent that `digiwhistPrice` is DIGIWHIST's "best price" preferring the award value. **So Italy's winner-premium provenance is unverifiable from the 30 GB dump — the only real VERIFY route is external: download ANAC's `aggiudicazioni` bulk dataset and CIG-match a sample** (the ANAC-access friction the Oct-14 log flagged). Decision for now: use `digiwhistPrice` as the award price with this caveat stapled to any Italy winner-premium number; escalate to the ANAC check only if that number becomes load-bearing.
- **Comparability:** for an apples-to-apples generalization claim, recompute **Cyprus** winner-premium from `digiwhistPrice` too (won't move — digi==final there — but harmonizes the method).

### Next country: **codename RO (Romania)**
Queued after Italy. Rationale and the one caveat:
- `finalPrice` completeness is **country-by-country and unpredictable** — Cyprus 88% → Italy 0% on the *same* schema/pipeline, **uncorrelated with corruption level**. So "RO is higher-corruption → worse data" does NOT follow.
- **Gating probe — DONE (VERIFIED 2026-10-15).** Extracted `data-ro-ndjson.zip` → **24 years (2001–2026), 9.3 GB** in `ratsniffer/data/` (gitignored). Probed RO 2015 (10,977 scanned, 10,252 awarded). **RO is in the Cyprus camp, not Italy's** — the provenance problem does NOT apply:
  ```
                   estimatedPrice  finalPrice(raw)  digiwhistPrice  indicators
  RO 2015              70.2%           87.5%           99.2%          100%
  ```
  **Raw `finalPrice` present on 87.5%** (Italy 0%), and where both raw-final + digi exist (n=8,968), **`digi == final` 100%** — the Cyprus-style confirmation works, so RO's award price is *verified*, and winner-premium can be built from raw `final/est` with zero DIGIWHIST dependence. single-bid 68.3% (same winner-only artifact, milder than Italy's 74% / Cyprus's 81%); awarded rate ~93%.
- **RO winner-premium (raw `final/est`, fully independent):** computable on 38.8% of awarded, **median 1.000, 71.6% ≥0.98**, 19.6% <0.90. Note the cluster at the estimate (median 1.000 vs Cyprus 0.92 / Italy 0.962) — awards hug the ceiling far more in RO: either a reporting convention (final defaults to estimate) or genuine ceiling-hugging. One year; don't over-read, but flag it for the concordance run.
- So the earlier "RO might be worse" worry is **inverted** — for the concordance's one independent signal, RO is the **strongest** of the three countries.
- RO's **primary** value is unchanged by any of this: **DNA's large volume of adjudicated procurement cases** = the best EU path to *real labels* (hand-linking court cases → opentender records), the one thing the project still lacks. That holds even if RO's price fields are weak.

### Not done / open
- **No Italy AUC computed** — field population only.
- **Concordance script is still uncommitted** (never saved from the Cyprus session) — it's a from-scratch rebuild. Adaptations for Italy: use `digiwhistPrice` not `finalPrice`, restrict to 2015+, stream.
- De-circularize (winner-premium only) still pending — and for Italy it carries a permanent asterisk: that signal *is* winner-premium, whose award-price provenance is unverifiable in-dump (see the gate finding above). A de-circularized Italy number is only as trustworthy as the `digiwhistPrice`-is-award assumption.

### Romania real-labels arc — the first measured catch-rate against confirmed corruption (all VERIFIED this session)
The session turned from "does our logic agree with experts?" to "does it catch firms a court actually sanctioned?" Three tests, ending in a **powered null**.

- **Concordance (RO 2015, our flags vs opentender DIGIWHIST integrity):** AUC **0.854** full / **0.766** de-circularized (winner-premium only, vs an integrity composite with single-bid+procedure removed; RO's `advertisement/decision_period` indicators vary, so the baseline isn't degenerate). Higher than Cyprus's 0.80 → the agreement generalizes. **But concordance is agreement-with-a-heuristic, not catching a thief.**
- **Contract-level flags on 8 image-seed sanctioned firms (365,679 RO tenders):** combined flag **1.82 vs 1.84 baseline — no lift.** First time real labels answered back; they said no.
- **Firm-level HHI score `pre_sanction.py` (T=2012/14/16, held-out blacklist label):** AUC **0.48–0.62**, *inside* the label-shuffle band; matched-control sign-test p ≥ 0.34. **Underpowered null** (≈6 distinct firms; SIVECO triple-counted via name variants; `SANCTION_YEAR` empty so not a true pre-sanction test). Per-firm, the only firm it flagged was **Condmag** (pct 0.90–0.96) — the one whose mechanism (concentrated-buyer bid-rigging) matches HHI; **Siveco ranked clean** (its crime was cover-bidding, which HHI can't see). Mechanism-match, not noise.

### The decisions, verified against press of the Council's announcements (not the decisions themselves)
Built `data/sanctions.csv` (firm, role, mechanism, altitude, infr_start/end, market, buyer, decision_date, fined, conf). Key corrections vs the original image-seed: **Armax dropped** (2014 probe, outcome unconfirmed); **Electrica is buyer-side** (organiser facilitation, Dec 77/2017, excluded from supplier positives); **AEM participant, not fined** (leniency); **OYL is a positive** (road-maintenance market-sharing, 5 counties, decision 2026-01-14); added co-defendants Inspet/Moldocor/TMUCB/Elster/Landis+Gyr/Ecro. Mechanisms split by *altitude*: single-tender bid-rigging (Condmag, Siveco/Intrarom — test bidder-pairs, **not** HHI) vs multi-tender cartel/market-sharing (meter cartel, OYL — HHI/rotation) vs buyer facilitation (Electrica).

Rigged-tender identifiers pulled (`data/rigged_tenders.csv`, from press of the Council decisions; decision PDFs 503'd):
- **Butimanu-Brazi** gas connection / Transgaz / 2009 / **Inspet won** (Condmag cover). Fines Inspet 7.30M / Condmag 4.55M lei.
- **Giurgiu-Ruse** 20" pipeline / Transgaz / ~2011 / **Decision 72, 14.11.2012**. TMUCB 11.38M / Moldocor 2.24M lei.
- **APIA IT-system** framework / APIA / 2008 / **Siveco won** (Intrarom cover). Siveco 5.88M / Intrarom 2.13M lei. (Triggered by the Court of Accounts.)

### `infringement_test.py` — the powered null (the real answer to "how accurate at catching it")
Contract-level test, de-diluted by scoring only contracts **won by a sanctioned firm inside its infringement window**, vs **matched controls (same CPV-division + year, clean winner)**. One pass over 365,679 awarded RO tenders. Coverage is fine — we locate the firms' in-window contracts (Energobit 116, AEM 83, Siveco 23, Moldocor 18, …); OYL/Autoprima/Saga found 0 (infringement dates blank).
```
positives (sanctioned firm, in infringement window)   350
matched controls (same CPV-div + year, clean winner)  113,972
combined-flag mean:  positives 1.92   controls 1.93
AUC(label vs flag) = 0.489      recall@FPR10% = 0.000
label-shuffle x20  = 0.506 +/- 0.013   (real AUC sits inside it)
```
**This is a well-powered null** (350 positives, shuffle std 0.013) — unlike the firm-level run. The contract-level invariant flags (single-bid, non-open, winner-premium) **do not separate** the infringement-period contracts of these cartels from matched clean contracts. **Honest catch-rate against real confirmed-corrupt Romanian bid-rigging: ~0% (AUC 0.49, recall@10%FPR 0.00).** The failure is **discrimination, not presence** — and the flags are near-saturated in RO (single-bid 77%), so they carry little range.

### The one caveat that stops this being the final verdict
The label is still *"won by a sanctioned firm during its infringement window,"* not *"this specific contract was the rigged one."* Condmag won 7 contracts in 2009 but only **Butimanu-Brazi** was rigged; of the 350 positives, only ~a couple dozen are the actual rigged tenders, the rest legitimate work. So this proves **"no firm-in-window signal"** (a hard bound) but can't yet isolate **"blind to the specific rigged tender."** The last de-dilution — match the exact tenders in `rigged_tenders.csv` by title keyword (Butimanu-Brazi / Giurgiu-Ruse / APIA-IT) + buyer + year, giving a handful of truly-rigged contracts vs controls — is the only remaining test that could move the number. **Not yet run.**

### Also this session
- `CLAUDE.md` gained **"No labels as detector inputs (evaluation integrity)"** — no blacklists/sanction lists as features; accuracy gains must be behavior-based + held-out; recall@FPR / precision@k over accuracy; a derivative/transform adds no information. Prompted by catching a blacklist-as-feature suggestion mid-session.
- Settled what the project's **partial derivative** actually is: `ddx`/`sensitivity` in `sandbox.html` is ∂(total true frontline delivery)/∂(node capture or audit), central-difference — computed on **hidden ground truth**, never ported to `ratsniffer/*.py`. It's a reshaping of the *label*, so it could never add held-out accuracy.
- `data/` now carries `sanctions.csv` + `rigged_tenders.csv` (labels, trackable) alongside the gitignored `*.ndjson`.

### `exact_tender_test.py` — the capstone, and a structural ceiling (VERIFIED)
The last de-dilution: find the three *specific* rigged tenders in the RO data by title keyword + buyer + year (an inspection, not a stat test — n is 1–3 per case). Result:
- **APIA-IT: 0 candidates.** The 2008 Siveco/Intrarom tender is **not in the opentender dump** (2007–09 RO coverage too thin / APIA not captured). Untestable.
- **Giurgiu-Ruse: 6 hits, none the pipeline.** All Giurgiu-*county* noise (bridge/CFR/fire-safety-IT/water-analysis). The Transgaz 20″ gas pipeline tender **not found** — absent or titled differently.
- **Butimanu-Brazi: found the semantically-exact tender** — 2010 `Racord g.n. Butimanu-Brazi ... centralei de cogenerare Brazi`, won by `INSPET + TMUCB`, `proc=NEGOTIATED_WITHOUT_PUBLICATION`, flags 2/3.

**The decisive observation: `nbids=1` on every candidate across all three cases.** The crime is **cover-bidding** (colluders submit *losing* bids to fake competition), but RO opentender logs **only the winner** — so the one observable that *is* the evidence (the loser's correlated cover-bid) is **systematically absent**. On Butimanu the 2/3 is the winners-only artifact (single-bid-logged) + a genuinely odd negotiated-without-publication award — **not** detection of the rigging, which is invisible.

**Capstone verdict for the whole Romania arc:** catch-rate against confirmed RO bid-rigging is **~0%, and structurally capped** — not a wrong invariant or a bad threshold, but that **cover-bidding is unobservable in winners-only procurement data**. No feature detects a cover-bid that was never logged, and 2 of 3 rigged tenders aren't even locatable. The honest unlock is **bid-level data that includes losing bids** (or the exact SEAP procedure IDs from the decision PDFs — both 503'd / absent here), not a better model. This closes the Romania real-labels line: the ceiling is the data, and we found it by chasing the crime down to the individual contract.

### Postscript — the single-bid signal was an artifact the whole time (`lots[].bidsCount`)
Chased "find bid-level data with losing bids." Public RO bid-level data effectively doesn't exist (OpenTender RO = **0 tenderers** at the registry level; SICAP bulk export broken; OCDS never published bidders below-threshold). **But** the real bid *count* was in our data all along — field **`lots[].bidsCount`** (DIGIWHIST's TED-recovered count), populated on **37.9%** of awarded RO tenders. We'd been counting the winner-only `bids` array instead. Proof it's real: **844 tenders where our `nbids==1` but `INTEGRITY_SINGLE_BID==100` (multi-bid)** — the count survived, our reading hid it.

Correction this forces (RO 2015):
```
ARTIFACT single-bid (our nbids==1):   68.3%   <- every test this session used this
TRUE single-bid (bidsCount==1):       44.5%   <- real, on the 37.9% that carry it
real bid-count spread: 1:1727 2:646 3:366 4:264 5:174 6+:708
```
So **every session number that used single-bid (concordance, `infringement_test`, blacklist cross-check) ran on an inflated artifact** — not comparable to a rerun on real `bidsCount`.

**What it unlocks vs doesn't — two different mechanisms:**
- **Unlocks:** genuine single-bidding (sole-source / no-competition typology) on the ~38% subset. Cheap, real upgrade; de-artifacts the concordance.
- **Does NOT touch cover-bidding** (the actual RO cartel cases), for two reasons: (1) `bidsCount` is a *count, not identities* — loser names still absent (`INTEGRITY_MULTIPLE_VALID_BIDS` = 100% INSUFFICIENT_DATA); (2) **cover-bidding tenders are multi-bid by design** — Butimanu (Condmag+Inspet) and APIA (Siveco+Intrarom) would read `bidsCount≥2`, i.e. "competitive," so even the true count correctly stays silent. Count obtainable, identities not; the capstone ceiling stands.

**Rewired and re-ran (single-bid → `bidsCount`; `concordance.py` + `infringement_test.py`):**
```
                       pre-rewire(artifact)   rewired(bidsCount)
single-bid flag rate         0.683                0.168
FULL concordance AUC         0.854                0.728
DE-CIRC (winner-prem only)   0.766                0.766
infringement AUC             0.489                0.521
infringement recall@FPR10%   0.000                0.034
infringement label-shuffle     --            0.504 +/- 0.013
```
The rewire made the numbers **honest, not better**. FULL concordance deflated (0.854→0.728) as the inflated single-bid fell away; the **independent DE-CIRC held exactly at 0.766** — now the real headline. The infringement test moved from just-below to just-above chance (0.489→0.521, recall 0→3.4%) but **0.521 vs shuffle 0.504±0.013 is within noise — still a null.** And it **confirms the ceiling rather than lifting it, for the predicted reason**: a *correct* single-bid flag fires on genuine single-bidding, but cover-bidding reads `bidsCount≥2` by design, so the flag correctly stays silent on the actual cartel contracts. De-artifacting couldn't help because single-bid was never the right signal for cover-bidding.

**Honest final state of the Romania arc:** independent concordance with experts **AUC 0.766** (de-artifacted, stable); catch-rate against confirmed bid-rigging **≈ chance** (AUC 0.52, recall@10%FPR 3.4%), and structurally so — the crime is cover-bidding, and the data has neither the loser identities nor a single-bid tell for it. Files added this session: `concordance.py`, `infringement_test.py`, `exact_tender_test.py`, `pre_sanction.py`, `data/sanctions.csv`, `data/rigged_tenders.csv`.

---

## Session log — 2026-10-17

### Ukraine ProZorro — architecture findings, AMCU cartel data, cover-bidder pattern confirmed

**Why Ukraine:** Romania hit a structural ceiling (cover-bidding undetectable in winners-only data). Ukraine's **ProZorro** is the first procurement source with bids including losers — the exact data type needed to test cover-bidding detection. Ukraine also has **AMCU** (Antimonopoly Committee) enforcement decisions with named firms, fine amounts, and decision dates — real labels from a publishing regulator.

**AMCU cartel labels built (`data/amcu_cartels.csv`):**
Six cartels resolved from AMCU press releases and decisions: `kyiv_waste` (9 firms, waste collection Kyiv, fine 313M UAH, 2026-07-31), `barite_ukrgaz` (2 firms, Ukrgazvydobuvannya barite, 2025), `electricity` (2 firms, De Trading + ТЕК, 110M UAH total, 2026-09-08), `mykolaiv_construction`, `medical_infra`, `pivdennoukrainsk_school`. Cyrillic `firm_uk` names filled from press reporting; `edrpou` column initially blank (AMCU site 403'd).

**ProZorro API architecture — the wall:**
- **Feed API** (`public-api.prozorro.gov.ua/api/2.5/tenders`): full tender detail including all bidders + amounts, date-seekable. ✓
- **Search bridge** (firm → tenders): does not exist as an open endpoint. Tested 5 URL patterns — all 404/405/422.
- **bi.prozorro.org** (Qlik Sense BI): free, has firm-level search and tender lists. Export is image-only (no CSV/Excel on public tier). JavaScript DOM extraction (`title` attributes) empty — Qlik virtualizes rows without title attributes.
- **Clarity Project** (paid API, ~$30/mo): found during search, rejected.

**Cover-bidder pattern confirmed via bi.prozorro.org:**
Searched `Де Трейдинг` in Карточка учасника (Пропозиції). Found:
- EDRPOU: **42699760** (De Trading) — В "чорному списку" АМКУ: **Так** (on AMCU blacklist, confirmed)
- **110 lots, 0% wins** across all of them — pure cover-bidder by behavior
- Top co-bidder: **ТОВ "ТЕК" | 36530971** appearing in **104 of 107 shared lots**
- **ТЕК** = abbreviation of **Т**оргова **Е**лектрична **К**омпанія = the other AMCU-named firm
- AMCU fined ТЕК more (60M vs 50M UAH) — consistent with winner/cover-bidder asymmetry

Both EDRPOUs filled in `amcu_cartels.csv`: De Trading 42699760, Торгова електрична компанія 36530971.

**Feed scan — kyiv_waste hits obtained:**
Ran `prozorro_window.py` from 2019-02-01. After ~1hr, 12 days of feed covered (2879 lots, 11 `kyiv_waste` cartel-tagged). Electricity cartel tenders from Feb-Mar 2019 completion dates fall later in the feed (April-June 2019 by `dateModified`) — missed in this window. Brute-force scan of all 2019 too slow (~35 hrs on this machine). Offloaded to a second laptop (Linux Mint, Ryzen 3) via SSH + `nohup`:

```bash
nohup python3 prozorro_window.py 2019-01-01 5000000 data/prozorro_2019_2021.ndjson > scan.log 2>&1 &
```

ETA ~5 days for full 2019–2021 coverage. Progress checkable via `ssh raven@OTHER_IP "tail -3 ~/Documents/Ratsniffer/scan.log"`.

### Algorithm improvements — four shipped, one bug fixed

**Bug fixed (`procurement.py` line 32):**
`losers = b[:1]` → `losers = b[1:]`. The old code computed std of a single-element array (always 0), making `rel_distance` always 0 and inactive. Now computes std of all non-winner bids, as intended. `rel_distance` is now active in `cartel_eval.py` output.

Also removed a duplicate `procurement_world()` definition (lines 8-23 shadowed by 51-67; only the second, correct version kept).

**1. `bid_ratio` (new feature):** `b[1] / b[0]` for k≥2 bids (2nd-lowest / winner). Captures the cover-bidder gap without requiring ≥3 bids. Added to `PROC_FEATURES` and `tender_features()` return.

**2. IsolationForest (`cartel_eval.py`):** fit on clean tenders only (`X[y==0]`), scores all tenders. Satisfies the CLAUDE.md required check ("IsolationForest is fit on honest nodes only"). Result on kyiv_waste data: **AUC 0.713, recall@FPR10% 0.714** — best result so far. Label-shuffle x20: **0.485 ± 0.079** — IsolationForest is well outside the shuffle band.

**3. Co-bidder HHI (`cobidder_hhi()`):** firm-level concentration of co-bidders (Herfindahl index). De Trading's HHI would be near 1.0 (always bids against the same ТЕК); genuinely competitive firms have dispersed co-bidder pools. Reported as a diagnostic (top-10 most concentrated firms); not yet joined as a per-tender feature.

**4. Precision@k:** reports `precision@10/20/50` on `bid_cv` scores. Currently 0.000 at all k (7 cartel lots in 6128 = 0.1% base rate — dilution too severe for top-k to land). Will improve with full scan data.

### Verified results on real cartel data (7 kyiv_waste lots, 6128 total)

```
[per-screen AUC: cartel-tagged vs clean]
  bid_cv           0.696
  winner_premium   0.357
  n_bidders        0.537
  rel_distance     0.543  <- now active (bug fixed)
  bid_skew         0.525
  bid_kurt         0.503
  bid_ratio        0.618  <- new feature

[IsolationForest on clean-only]  AUC 0.713  recall@FPR10% 0.714
[iso shuffle x20]  0.485+/-0.079  (expect ~0.5)
[label-shuffle x20] best single-screen AUC  0.611+/-0.055
```

`bid_cv` (0.696) and IsolationForest (0.713) both above shuffle band. Too few cartel samples (7) to treat magnitudes as stable — directional only. LOCO test requires ≥2 cartels; pending full scan.

### Caveats and open threads
- **Dilution:** firm-level labels tag every tender a cartel firm bid on, not just rigged ones. Near-chance is the dilution ceiling; exact rigged-tender IDs would de-dilute but AMCU decision PDFs are 403-blocked.
- **One cartel only:** kyiv_waste is waste collection; electricity cartel data not yet in dataset. LOCO impossible until scan completes.
- **Co-bidder HHI at 1.0 for all top-10:** scanner has only covered 12 days of 2019; most firms appear in just one tender. HHI becomes meaningful at fuller coverage.
- **Scan still running** on second machine; results pending.
- **devlog correction:** `prozorro_window.py` argv handling had a bug — 3rd argument (output path) was not passed to `main()`, so the custom output filename was ignored. Fixed in the version running on the second laptop.

---

## Session log — 2026-10-18

### Algorithm improvements shipped

**`loser_cv` (new feature):** CV of non-winner bids only (`std(b[1:]) / mean(b[1:])` for k≥3). Captures cover-bid loser clustering directly — in a cover-bid tender, losers are tightly bunched just above the winner → low `loser_cv`. Added to `PROC_FEATURES` and `tender_features()` return list. Also added `loser_cv = 0.0` to the `else` branch (k<3).

**Generator hardening (`procurement_world()`):** Cover-bid losers widened from `win * rng.uniform(1.0, 1.03)` to `win * rng.uniform(1.002, 1.0 + spread)` where `spread ~ U(0.01, 0.08)`. Winner floor lowered from 0.93 to 0.85. Added 15% of clean tenders as naturally-clustering competitive bids (`mu_b * rng.uniform(0.97, 1.03)`). Result: `winner_premium` single-feature AUC dropped from **1.000 → 0.959** — generator no longer trivially easy.

**`firm_win_rate` + `pct_chronic_losers` added to `cartel_eval.py`:** Pre-computes per-firm win rate across all tenders (firms with ≥5 appearances), then for each tender reports fraction of bidders who historically never win. Motivated by De Trading's 0% wins over 110 appearances — undetectable from single-tender features. Not yet wired into the IsolationForest feature vector; present as helper functions.

**JSON error handling in `cartel_eval.py`:** Added `try/except json.JSONDecodeError` in both `load()` and `cobidder_hhi()` to handle truncated last lines when the file is copied mid-write.

### Synthetic eval after generator hardening

```
procurement: 750 tenders, 173 rigged (23.1%), 30 buyers

[single-feature AUC]
  single_bid       0.676
  bid_cv           0.038   <- inverse separator (low = rigged)
  winner_premium   0.959   <- was 1.000, now below WARN threshold
  n_bidders        0.263
  rel_distance     0.408
  bid_skew         0.443
  bid_kurt         0.655
  bid_ratio        0.106
  loser_cv         0.048   <- inverse separator (low = rigged)

[held-out by buyer x10]  ROC 0.966+/-0.008
                         recall@FPR10% 0.897+/-0.053
[label-shuffle x10]      ROC 0.472+/-0.223  (expect ~0.5)
```

No leak, no single feature >0.95. Generator is no longer trivially easy.

### ProZorro scan progress and real-data eval

**Scan infrastructure:** Second laptop (Linux Mint, Ryzen 3, `192.168.100.21`) running `prozorro_window.py`. SSH key installed (`ssh-copy-id`). Scan died at 312,900 scanned / 23,696 wrote due to ProZorro API timeout. Last date in feed: **2019-03-21**. Restart command (append mode):

```bash
cd ~/Documents/Ratsniffer/ratsniffer && python3 prozorro_window.py 2019-03-21 5000000 >> data/prozorro_ua.ndjson 2>scan.log
```

**Data pulled (15MB snapshot, 28,277 lots):**

```
lots 28277  cartel-tagged 39  clean 28238
cartels: electricity=4  kyiv_waste=33  medical_infra=1  pivdennoukrainsk_school=1

[per-screen AUC]
  bid_cv           0.607
  winner_premium   0.476
  n_bidders        0.543
  rel_distance     0.538
  bid_skew         0.497
  bid_kurt         0.462
  bid_ratio        0.566
  loser_cv         0.545

[IsolationForest on clean-only]  AUC 0.584  recall@FPR10% 0.231
[iso shuffle x20]  0.522+/-0.057

[leave-one-cartel-out]
  electricity   n_pos=4   AUC 0.167  recall@FPR10% 0.000
  kyiv_waste    n_pos=33  AUC 0.490  recall@FPR10% 0.030
  medical_infra / pivdennoukrainsk_school: skip (n=1)
```

### Key findings

- **Electricity cartel confirmed in feed** — 4 tenders found (De Trading / ТЕК window around March 2019). LOCO test now live for the first time.
- **IsolationForest improved 0.530 → 0.584**, recall@FPR10% 0.056 → **0.231** — more data helping.
- **`loser_cv` active at 0.545** on real data — contributing alongside `bid_cv`.
- **Electricity LOCO AUC 0.167** — worse than random. Cross-sector sign flip: model trained on kyiv_waste (waste collection, many bidders) predicts electricity tenders as clean. Same disease as the synthetic cross-family inversion finding. More electricity hits needed before this number is stable.
- **Dilution still the binding constraint** — 39 cartel-tagged out of 28,277 (0.14% base rate). Precision@k = 0.000 at all thresholds. AMCU decision PDFs (exact rigged-tender IDs) remain 403-blocked.
- **HHI still 1.000 for all top-10** — scan coverage too sparse for firm co-bidder concentration to be meaningful.

### Open / next
- Restart scan on Mint laptop from 2019-03-21 (append mode, see command above).
- Pull fresh snapshot once scan reaches ~500k scanned — electricity window should widen.
- Wire `pct_chronic_losers` into the IsolationForest feature vector once enough firms have ≥5 appearances.
- LOCO test needs more electricity hits (≥5) to be reliable — keep scanning.
