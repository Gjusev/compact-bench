# NOTES.md — research log

## Existing-implementation search (2026-11-15, before building)

Query set: web searches for `arXiv 2611.05306` + implementation/GitHub phrases;
GitHub code search `2611.05306 in:file` (370 hits, dominated by benchmark
indexes and digest posts, none a second repro of the mechanism).

### Found

1. **`che-shr-cat/short-context-agent`** — https://github.com/che-shr-cat/short-context-agent
   - MIT license (verified via GitHub API `licenseInfo`), created 2026-11-05, Python.
   - Self-described "open reproduction of 'You Don't Need Long Context'",
     packaged as a **Claude Code plugin/marketplace skill + reference
     harness** (`scripts/sac_harness.py` with `fha`/`eocc`/`sac` regimes,
     handoff-brief compaction prompt, selective-reading protocol).
   - Its README states: "**Method reproduction, not (yet) results
     reproduction.** … the benchmark numbers … have not been re-run with this
     code."
   - **Decision: not forked.** It contains no benchmark: no task suite, no
     success/peak-token/cost metrics, no regime comparison table, no offline
     deterministic mode. compact-bench fills exactly that gap (runnable
     harness + metrics + table), which the owner's repo plan specifies.
     Credited here and in the README; not affiliated.

2. **No official code release by the paper's authors.** The report used the
   public **mini-swe-agent v2.4** harness plus in-house compaction changes
   that were not released. Sources:
   - https://www.aiagentsinfo.com/research/you-dont-need-long-context —
     "It uses the public mini-swe-agent harness, version 2.4… This page did
     not find a separate code release for those harness changes."
   - https://arxiviq.substack.com/p/you-dont-need-long-context — "Code: N/A
     (unofficial re-implementation)".

### What that means for this repo

- README may claim: **first open *benchmark harness*** for the paper's three
  regimes (a companion open *method* repro exists; see above). It must NOT
  claim "first open implementation" flatly.
- Everything here is built from the paper's public descriptions (abstract,
  alphaxiv/arxiviq/aiagentsinfo digests, HF paper page).

## Paper facts used (for later real-model runs)

- Three regimes: FHA / EOCC (threshold θ, settings written "limit/threshold",
  e.g. 24K/18K) / SAC (one action per context).
- Headline: Opus 4.5 SWE-bench Verified 70.0 (FHA) → 70.2 (SAC), best EOCC
  74.8; GPT 5.6 Sol 84.4 → 82.4, best EOCC 88.8. Peak live context
  130–200K → 15–37K.
- Serving cost: decoding at 256K window costs 3.6–7× more per output token
  than 16K on identical H100s (Qwen 3 Coder Next worst). Cost ratio r ≈ 0.20
  used for window-price interpolation (Appendix B).
- Compaction should be a **forward-looking handoff brief**, not a generic
  summary (Appendix A): task near-verbatim, current step, plan + done
  criteria, pointers to relevant files. compact-bench's structured state
  block (progress counter + truncated last observations) follows this shape.
- Long-input trick: store big inputs as files, read slices via search/read
  tools — implemented here as the `refactor-long-config-read` task.

## Tooling constraints discovered

- System Python is PEP 668 (externally managed); no installs possible →
  zero-dependency core enforced; tests run with plain `python3 -m unittest`
  from repo root (`tests/__init__.py` puts `src/` on sys.path).
- Network imports stay lazy (stdlib `urllib` inside `ZaiClient.chat`), so the
  offline suite never touches the network.
