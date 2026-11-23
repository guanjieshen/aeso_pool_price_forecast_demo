---
name: start-here
description: Use first for any request about this repo, however it is worded ("forecast looks wrong", "add a card", "rerun the backtest", "job failed", "update the deck numbers"). Turns it into a precise task, asks at most two questions, gets a yes, then hands over to the right skill. Changes nothing itself.
---

# Start here: turn the request into a precise task

## 1. Understand it

| They want... | Hand over to |
| --- | --- |
| To deploy, run, retarget or tear down anything; a failed job or pipeline fixed | **deploy-and-run** |
| A model, weight, metric or the backtest changed; a new `@champion` | **retrain-and-backtest** |
| An app card, the ops action form, the Genie space or a Genie One prompt changed | **change-the-app-or-genie** |
| Evidence, `FE_BAR.md` or deck numbers brought up to date | **refresh-evidence** |

If it is unclear, ask **at most two short questions** with examples ("Is this the hourly forecast or the weekly retrain?").

## 2. Write the precise task and get a yes

Write back in plain words: **what** they asked for, **what will change** (files, jobs, tables), **what could go wrong** and how to undo it, and **what they will see** when it is done. Ask "Shall I go ahead?" and wait for a clear yes.

## 3. Hand over

Follow the chosen skill. Whatever it is, the rules in [AGENTS.md](../../../AGENTS.md) apply: no secrets, every number traces to a run, deploy only through the bundle.
