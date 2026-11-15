# ROADMAP.md

Ordered next steps. **Item 1 is owner-approval-gated and manual** — no spend
without the owner's explicit OK.

1. **First real-model run** *(owner approval required — est. budget $10–25 of
   the Z.ai Coding Plan subscription)*
   - Get explicit owner approval for the spend.
   - `export COMPACT_BENCH_ZAI_KEY=<Z.ai Coding Plan key>`
   - Wire `LLMPolicy` into `eval/run_bench.py` (`--policy stub|llm` flag),
     run all 12 tasks × 3 regimes with model `glm-5.3-flash` ONLY.
   - Acceptance: a real-model table committed under `results/` with the same
     columns as the stub table, plus per-task transcripts; README "Honest
     status" updated to separate "harness validated" from "first model run done".
   - STOP rule: on any billing/endpoint error, STOP and report. Never fall
     back to pay-per-call or another provider/model.
2. **Scale + variance**: parameterise task seeds/variants (e.g. 3 SQL
   databases, 3 grids per template) so success rates are rates, not
   12-point point estimates; add per-category breakdown columns.
3. **Threshold sweep**: run EOCC at θ ∈ {100, 150, 250, 400, 10⁹} on the stub
   and later on real runs; reproduce the paper's "limit/threshold" grid and
   the finding that only few settings lose >2 points.
4. **Real compaction brief**: replace the extractive stub state block with an
   LLM-written handoff brief (structured prompt per paper Appendix A) as a
   fourth regime (`eocc-llm-brief`), keeping FHA/EOCC/SAC comparable.
5. **BFCL v3 multi-turn subset** (public, optional contrast): adapter that
   runs the same three regimes over a BFCL v3 multi-turn slice; keep it
   offline-testable with a cached fixture.
6. **CI**: GitHub Actions running `python3 -m unittest` on push (free, no
   secrets). Any workflow that would spend API credits must be
   `workflow_dispatch` (manual) with the scheduled trigger commented out and
   an owner-approval TODO.
