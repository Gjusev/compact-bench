# compact-bench

[![tests](https://github.com/Gjusev/compact-bench/actions/workflows/tests.yml/badge.svg)](https://github.com/Gjusev/compact-bench/actions/workflows/tests.yml)
[![dependencies](https://img.shields.io/badge/dependencies-0-success)]()
[![python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A deterministic, zero-dependency benchmark harness for the **three context
regimes** of *"You don't need long context"* (Belcak et al., NVIDIA,
[arXiv:2611.05306](https://arxiv.org/abs/2611.05306)):

| Regime | Meaning |
|---|---|
| **FHA** — Full-History Accumulation | every action + observation stays in context (baseline) |
| **EOCC** — End-of-Conversation Compaction | when context crosses a token threshold, reset to task + bounded handoff state |
| **SAC** — Single-Action Compaction | after *every* action, reset to task + state (one action per context) |

The paper's core claim: aggressive compaction sacrifices little to no task
accuracy while collapsing peak context (Opus 4.5 on SWE-bench Verified:
70.2 SAC vs 70.0 FHA with peak context 32K→8K), so long-context models may
be unnecessary. compact-bench tests that **mechanism** on small, fully
deterministic tasks, offline, with a scripted stub agent — no API needed.

Unofficial, independent implementation. Not affiliated with NVIDIA or the
paper's authors.

## Existing-implementation check (done before building)

- **One prior open repro exists**: [`che-shr-cat/short-context-agent`](https://github.com/che-shr-cat/short-context-agent)
  (MIT, 2026-11-05) — the paper's regimes packaged as a **Claude Code skill +
  reference harness**. We did **not** fork it, because it does not contain a
  benchmark: no task suite, no metrics, no regime comparison table. Its own
  README states "Method reproduction, not (yet) results reproduction."
  compact-bench fills the gap it leaves open: a **runnable offline harness**
  with deterministic tasks, peak-context/cost accounting, and a 3-regime table.
- **No official code release**: the paper built on public mini-swe-agent v2.4
  plus in-house compaction changes that were not released (see NOTES.md for
  sources).

## Quickstart

```bash
# offline harness validation (no API key, no installs; Python >= 3.9 stdlib only)
python3 -m unittest                 # 27 tests from repo root
python3 eval/run_bench.py           # prints the 3-regime comparison table
```

Real-model runs (owner-approval-gated, see ROADMAP.md item 1):

```bash
export COMPACT_BENCH_ZAI_KEY=...            # Z.ai Coding Plan key
python3 -c "from compact_bench.llm import ZaiClient, LLMPolicy; ..."
```

## Layout

```
src/compact_bench/
  agent.py         agent loop with configurable regime (fha/eocc/sac) + stub policy
  compaction.py    EOCC/SAC compaction: bounded, structured handoff state
  tokens.py        deterministic token estimation (chars/4 heuristic)
  metrics.py       cost model + paper-style comparison table renderer
  llm.py           Z.ai Coding Plan client (glm-5.3-flash ONLY) + LLM policy
  tasks/           12 deterministic tasks: 4 sqlite SQL, 5 file refactoring
                   (incl. one long-input task), 3 mock grid navigation
eval/run_bench.py  offline bench: 12 tasks x 3 regimes -> table + JSON
tests/             27 tests, `python3 -m unittest` from repo root, zero deps
results/           committed offline stub-run results (labelled harness-validation)
```

Design note: the stub policy recovers **its own progress from the context**
(a structured `ACTIONS SO FAR: n` counter inside the handoff state), exactly
like a real model would. Compaction quality is therefore load-bearing — a
compaction that loses the counter makes the agent replay its plan from step 0,
and `tests/test_regimes.py::test_lossy_compaction_breaks_sac` proves the
harness detects it.

## Findings so far

*(from the offline stub runs — mechanism findings about the harness and the
regimes' shape, not model-quality results)*

1. **EOCC peak context is naturally capped at the threshold.** Because
   compaction fires the moment the estimate crosses θ, the peak EOCC context
   can never exceed θ (the overshooting exchange is compacted away before the
   next policy call). Observed: EOCC max peak == θ (150), FHA max 477.
2. **Threshold selection matters silently.** With a threshold never crossed,
   EOCC is *bit-identical* to FHA (`test_eocc_with_huge_threshold_never_compacts`)
   — a mis-tuned EOCC run looks exactly like the baseline. Always report
   compaction event counts alongside regime tables.
3. **At small scale, SAC can cost MORE than FHA.** SAC re-sends task + state
   every step (fixed overhead); with tiny task contexts that overhead exceeds
   FHA's accumulation (mean est. $/task SAC ≈ FHA at θ=150 on 12 tiny tasks).
   The paper's cost advantage materialises only on long contexts — confirmed
   here on the long-input task (~2 KB config file), where FHA's cost clearly
   exceeds SAC's. Predicts: benchmark compaction wins are context-length
   dependent, not universal.
4. **The progress counter is the load-bearing piece of compaction.** Dropping
   `ACTIONS SO FAR: n` from the handoff state (LossyCompaction) makes SAC loop
   its plan from step 0 until max-steps on every task. Any compaction prompt
   must make progress state explicit and structured — echoing the paper's
   Appendix A finding that generic summarisation underperforms handoff briefs.
5. **Bugs found while building** (each now covered by a test): the SAC loop
   initially compacted *before* appending the exchange, silently dropping the
   latest action (agent replayed step 0 forever — caught by the counter
   mechanism, not by an assertion); and `.strip()` on policy output corrupted
   `write` payloads whose content legitimately ends in a newline.

## Honest status

**Mechanism implemented + offline-tested.** All three regimes run end-to-end
on 12 deterministic tasks with a scripted stub agent; 27 tests green via
`python3 -m unittest`; the table below is **harness validation** — the stub
agent solves tasks by construction, so its 100% success rate checks harness
correctness, not model capability. **Paper numbers NOT reproduced** — no
real-model run has happened yet (owner-approval-gated).

### Offline harness-validation table (deterministic stub agent — NOT benchmark results)

```text
OFFLINE HARNESS VALIDATION — deterministic stub agent, NOT benchmark results
========================================================================================
Regime                 Tasks   Success  Peak ctx mean   Peak ctx max $/task est  Compactions
----------------------------------------------------------------------------------------
FHA  (full history)       12    100%          162            477   0.001965            0
EOCC (threshold)          12    100%          124            150   0.001834            4
SAC  (one action/ctx)     12    100%           97            118   0.001717           42
========================================================================================
```

Produced by `python3 eval/run_bench.py` (threshold 150 tokens, chars/4 token
estimate, list-price cost assumption — see `compact_bench/metrics.py`; raw
runs in `results/offline_stub_runs.json`).

## Owner rules (baked into CONTINUE.md and llm.py)

- LLM runs go **only** through the **Z.ai Coding Plan**:
  base `https://api.z.ai/api/coding/paas/v4`, model **`glm-5.3-flash` ONLY**
  (never another variant — `ZaiClient` rejects anything else).
- Key via env var `COMPACT_BENCH_ZAI_KEY`.
- Flat subscription: on a billing/endpoint error **STOP and report** — never
  fall back to pay-per-call or another provider.
- Real-model runs and the ~$10–25 budget estimate are **owner-approval-gated**
  (ROADMAP.md item 1, manual).

## License

MIT — see LICENSE.
