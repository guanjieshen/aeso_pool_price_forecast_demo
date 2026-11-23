# Protect the largest line in pipeline opex

**Day-ahead Alberta power price intelligence for Enbridge Liquids Pipelines**

Built on Databricks from public AESO market data · November 2026

---

## The outcome

**Move flexible pumping out of the hours that drive the power bill, and see spike risk a day before it lands.**

| | |
| --- | --- |
| **Where the money is** | In 2026, **2.6% of hours** (200 hours above $150/MWh) carried **35.8%** of a flat load's Alberta pool-price cost |
| **What a forecast can capture** | Over a 14-day walk-forward backtest the forecast's hour ranking captured **80%** of the savings perfect foresight would give, using only what was known the day before |
| **What that is worth** | Indicative 2026 to date, **per 10 MW of flexible load: about $0.93M** |
| **How fast, and getting better** | Refreshed **every hour**; the model **retrains and re-qualifies itself every week** |

Indicative value = perfect-foresight shifting value ($115,776 per flexible MW, 2026 to date) × backtest capture rate (80.3%). Flexible MW and 4 shiftable hours a day are planning assumptions to confirm with operations.

---

## The problem: power is the largest operating cost, and its price is spiky

- Alberta pump stations buy at the **hourly AESO pool price**: averaging **$33.72/MWh** in 2026, but hitting the **$999.99 cap** (May 25 and 28).
- Cost is concentrated: the most expensive **5% of hours carry 43.5%** of a flat load's cost.
- What drives it is **spare supply**: hours with under 2,000 MW of supply cushion are **6.1% of hours but 78% of spike hours**.
- Pumping is **partly flexible** (line-pack, tankage), but there is no forward, regime-aware view of when spikes will land, so flexibility goes unused or is used late.

Aligned to the Energy outcome map: **Connected Midstream** (optimize pipeline operations) meets **Precision Trading** (price and risk intelligence).

---

## Two levers, two owners

| | **Operate** | **Protect** |
| --- | --- | --- |
| Owner | Pipeline ops / control centre | Energy desk / power procurement |
| Question | "Which hours tomorrow should flexible pumping avoid?" | "How likely is a spike regime in the next 24 hours, and do we act?" |
| What they get | 24h ensemble forecast and hour ranking | P(spike) per hour, regime timeline, alerts that fire against the forecast |
| KPI | $ avoided per flexible MW, % of flexible MWh moved out of spike hours, power cost per barrel | Spike exposure (MWh bought above $150), alert lead time |

---

## For the executive sponsor: what it is worth

| Flexible load | Perfect-foresight ceiling (2026 to date) | At 80.3% capture (current champion model) |
| --- | --- | --- |
| 5 MW | $579k | $465k |
| **10 MW** | **$1.16M** | **$0.93M** |
| 20 MW | $2.32M | $1.86M |

- **Low cost to prove:** public data, serverless compute, one bundle deploys it.
- **Scales** to every Alberta station group, and to other power markets on the system.
- **Honest bounds:** the capture rate comes from a 14-day walk-forward backtest that sees only AESO's published day-ahead wind forecast, not the wind that blew; a pilot measures it on real load.

---

## For the domain owner: a day in the life

1. **Every hour** the forecast refreshes; **every Monday** a challenger model is trained and only replaces the champion if it is better.
2. **The energy desk** sees a rising Spike probability for the evening peak and sets an alert in AESO Market Pulse.
3. **The alert fires** against the latest forecast; **control centre logs a 10 MW load shift** out of the window.
4. **Next morning** they ask Genie: "What did that shift save versus the pool price?" Genie answers from the governed tables.

Every step is in the product today: alerts and shifts are written to **Lakebase**, copied to Delta, and queryable in **Genie**.

---

## How it works: one governed data journey

| Stage | Databricks | What it does |
| --- | --- | --- |
| Ingest | **Lakeflow Jobs** | Hourly AESO pool price, wind/solar forecast and history (99 metered assets), and supply fundamentals (load, capability net of outages, interties) archived as published |
| Transform | **Lakeflow declarative pipeline** | Silver/gold with data-quality expectations; only 1 of 8,004 hours imputed |
| Govern | **Unity Catalog** | Governed tags, lineage, the AESO key as a UC secret, least-privilege grants |
| Predict | **MLflow + UC registry + Lakeflow Jobs** | Regime HMM + Prophet + Monte Carlo ensemble, plus a supply-cushion model for tight hours; weekly challenger, model update trigger, gated `@champion` promotion |
| Serve | **Lakebase** | Low-latency live cards, ops action write-back |
| Surface + ask | **Databricks Apps + Genie** | AESO Market Pulse; Genie space (8/8 benchmark); screen-aware links into Genie One |

---

## Accuracy, honestly (14-day walk-forward backtest on day-ahead information, Oct 18 to 31, 336 hours)

| Forecast | MAE ($/MWh) |
| --- | --- |
| AESO published forecast | 16.24 · *published only hours ahead* |
| **Our day-ahead ensemble + cushion model** | **27.37** · **54% better than same-hour-yesterday** |
| Regime-aware Prophet | 30.36 |
| Same hour yesterday | 59.85 |

- The **regime model matters**: plain Prophet chased spikes (MAE 44.53); removing Spike hours cut it to 30.36.
- **Fundamentals beat more curve-fitting:** a model of price on the supply cushion, used only when the cushion is thin, was submitted as a challenger and promoted on the same 14 days (capture **73.1% to 80.3%**, MAE **31.79 to 27.37**). A Prophet-only tweak was rejected the same day.
- **Across three 14-day windows** (day-ahead information only): our forecast scores **87 out of 100** on load-shift capture, against 92 for AESO's hours-ahead forecast and 35 for same-hour-yesterday. The old champion scored 77.
- **No look-ahead:** we re-scored the old champion when we found the backtest was seeing the real wind; on the published wind forecast its capture is 73.1% on Oct 18 to 31, not the 90.2% it showed on a quiet window with the real wind.

---

## Trust: governed end to end

- **Unity Catalog governed tags** from the metastore's own tag policies (`domain=operations`, `layer`, `classification`, `data_product`).
- **The AESO credential is a UC secret**, read at run time and audited; only the job and the app's service principal hold READ.
- **Lineage** from the AESO API to every card and Genie answer.
- **Self-checking models:** a challenger only replaces the champion if it is better on the same days; every decision is logged, and live accuracy is monitored daily for drift.
- **Genie is grounded:** instructions carry units, Mountain Time, hour-ending and the AESO-forecast caveat; **8 of 8** benchmark questions matched hand-written ground truth.

---

## What we would validate with Enbridge operations

1. **Flexible MW** per Alberta station group, and how many hours a day it can move.
2. **Line-pack and tankage limits** that bound a shift.
3. **Alberta's share** of the power spend, and how much is on pool price vs fixed-price contracts.
4. **Who acts** on an alert (control centre, energy desk) and how fast.
5. **Load data** (SCADA / metered) to replace the flat-load assumption.

---

## Next steps

| When | What |
| --- | --- |
| 30 days | Pilot on one Alberta station group with real load data; measure capture rate live |
| 60 days | Add Protect: alert routing to the energy desk, hedge vs float decision support |
| 90 days | Extend to other power markets on the system; schedule recommendations in ops tools |

**Ask:** a 30-day pilot with one station group, an ops SME and an energy desk SME.
