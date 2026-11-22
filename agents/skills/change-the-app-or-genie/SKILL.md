---
name: change-the-app-or-genie
description: Use to add or change an AESO Market Pulse card, the ops action form, the Genie space instructions or questions, or a card's "Analyze with Genie" prompt.
---

# Change the app or Genie

1. **Read** [agents/app.md](../../app.md) (card to query map, design rules, Lakebase) or [agents/genie.md](../../genie.md).
2. **Card:** add the query to `app/app.py`, the chart to `app/static/index.html`, and a prompt template to the `GENIE_PROMPTS` map. Prompts name the tables and the values on screen.
3. **Run locally first:** `cd app && DATABRICKS_CONFIG_PROFILE=fevm-energy-canada uv run --with-requirements requirements.txt uvicorn app:app --port 8000`, then open `http://localhost:8000`. Check MPT times are not shifted 6 to 7 hours.
4. **Deploy** `databricks bundle deploy`, then `databricks bundle run aeso_market_pulse` and open the app URL.
5. **Genie:** edit `src/genie/`, deploy, then rerun `scripts/genie_benchmark.py` and commit the new score in `evidence/`.
