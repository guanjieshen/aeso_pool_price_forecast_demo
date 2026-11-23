---
name: refresh-evidence
description: Use after any run that changes results, before committing, to regenerate evidence/ from the live workspace and bring FE_BAR.md and docs/decisions.md numbers up to date.
---

# Refresh evidence

1. Make sure the runs you want are the **latest successful** ones (`aeso_hourly`, `aeso_weekly_retrain`, `aeso_evaluate_challenger`).
2. Export: `uv run --with databricks-sdk python scripts/export_evidence.py` (add `--only 03_ml_backtest.md` for one file).
3. Check each curated file is **under 9,000 characters** (`wc -c evidence/*.md`) and shows the run IDs and **SUCCESS**.
4. Find every number in `FE_BAR.md`, `docs/decisions.md` and `deck/deck.md` and confirm it matches `evidence/`. Fix the docs, never the evidence.
5. Scan before committing: `git grep -nE 'dapi|Bearer|billion'` returns nothing.
