# CONTINUE.md — read this first when an agent picks up this repo

## What this repo is

compact-bench is a repro scaffold for **"You don't need long context"**
(Belcak et al., NVIDIA, arXiv:2611.05306): a deterministic, zero-dependency
harness comparing the paper's three context regimes (FHA / EOCC / SAC) on 12
synthetic tasks (sqlite SQL, file refactoring incl. one long-input task, mock
grid navigation), with success rate + peak-context-tokens + est. $ per task
and a paper-style comparison table.

**Honest status: mechanism implemented + offline-tested. Paper's numbers NOT
reproduced.** The committed table in README/results is harness validation
from a scripted stub agent — never present it as benchmark results.

Read README.md, ROADMAP.md and NOTES.md fully.

## Working rules

- **Offline-first**: the test suite stays zero-dependency (Python stdlib
  only, PEP 668 blocks installs) and passes with
  `python3 -m unittest` from the repo root. Network imports stay lazy inside
  the method that uses them (`llm.py`).
- **Honest claims**: never state benchmark numbers that haven't been run.
  Anything measured goes in README/results with the exact command that
  produced it, and stub output is always labelled harness-validation.
- Cite the paper first (arXiv:2611.05306); independent, unofficial
  implementation — never imply affiliation with the authors. One prior open
  repro exists (che-shr-cat/short-context-agent, MIT — see NOTES.md); this
  repo is the first open *benchmark harness* for the paper's regimes.
- Commits in English, conventional-commit style (feat:/fix:/docs:).
- Before pushing: run the full offline suite; it must be green.
- **Models — Z.ai Coding Plan (mandatory, no other provider)**:

```bash
export COMPACT_BENCH_BASE_URL="https://api.z.ai/api/coding/paas/v4"
export COMPACT_BENCH_MODEL="glm-5.3-flash"
export COMPACT_BENCH_ZAI_KEY="<Z.ai Coding Plan key>"
```

  The model is pinned to **glm-5.3-flash ONLY** — `ZaiClient` raises on any
  other variant; never offer or document an alternative model.
  Flat subscription: on a billing/endpoint error STOP and report — do NOT
  switch providers or to pay-per-call to "get it working".

## Current task (do this now)

First real-model run (ROADMAP.md item 1) — **only if the owner has approved
the ~$10–25 spend in this session's context**:

1. Add a `--policy stub|llm` flag to `eval/run_bench.py` that swaps
   `StubPolicy` for `compact_bench.llm.LLMPolicy(ZaiClient())`.
2. Run all 12 tasks × 3 regimes with the Z.ai Coding Plan (glm-5.3-flash);
   write per-task transcripts + a real-model table to `results/real_run_*.json`
   with an honest label and the exact command used.
3. Update README "Honest status" and "Findings so far" from the actual run.
4. Acceptance: committed real-run table with the same columns as the stub
   table; `python3 -m unittest` still green.

**STOP point**: if no live endpoint/`COMPACT_BENCH_ZAI_KEY` is available, or
the owner has not approved spend, commit the tooling with the offline
harness-validation results marked "not yet run on a real model" and stop
there. Do not request keys, do not simulate model output.

## After that

Follow ROADMAP.md in order. One item per commit series.
