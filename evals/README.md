# Tripwire evaluation workflow

Run from the repository root using its Python 3.11+ environment. In the Evals
worktree the shared interpreter is `../HackHarvard/.venv/bin/python`; system
`python3` on this laptop is too old. The runtime loads credentials only through
`src/config.py`; Chalk Evaluations uses the existing Chalk CLI login.

```bash
../HackHarvard/.venv/bin/python -m pytest tests evals -q --basetemp=/tmp/tripwire-pytest
../HackHarvard/.venv/bin/ruff check .
../HackHarvard/.venv/bin/ruff format --check .
```

## Dataset and development

The exact frozen benchmark is committed at `evals/fixtures/eval_set.csv`; its
hashes, licenses, assumptions and label policy are in [DATASET.md](DATASET.md).
No download is needed to run it. To reconstruct from original UCI archives:

```bash
../HackHarvard/.venv/bin/python -m scripts.datasets.build --download
```

The builder downloads fixed UCI archives, never any URL from a message or dataset
row. It writes ignored `data/eval_set.csv` and the tracked frozen fixture. Do not
change labels after seeing predictions. The eight development cases are separate
from the benchmark and can be used to debug integration.

```bash
# New run directories for changed code; rerun exact command to resume unchanged code.
../HackHarvard/.venv/bin/python -m evals.run --mode checks --out evals/runs/dev-checks-new
../HackHarvard/.venv/bin/python -m evals.run --mode full --out evals/runs/dev-droid-new
```

`stub` returns a visibly marked failed placeholder for Tripwire. `checks` runs
real deterministic/RDAP checks and the verdict model, with no Droid/detonation.
`full` includes Droid and requires the real integration. Detonation is off by default; `--detonate-case ID` selects at most three cases
for the production Chalk sandbox path. Record those IDs before predictions. It never runs the Photon poller.

## Archived inference commands (all 3 run slots consumed)

The benchmark is complete. Do not start another full run. Commands below document
the original invocation; code hashes prevent resuming against changed code.
The full-run ledger is persisted **before** execution. Interrupted runs consume a
slot; resume them instead of starting another full run. Do not delete or reset
the ledger to bypass the budget.

```bash
../HackHarvard/.venv/bin/python -m evals.run --mode full --full-run --workers 2 --out evals/runs/full-v2 \
  --detonate-case url-69188 --detonate-case url-154131 --detonate-case synthetic-039
```

Full-v1 was interrupted after 10 predictions; its results are retained, and its slot
remains consumed. Full-v2 measures the newer production code at `f754dc8` and uses
slot 2 of 3. Do not resume v1 with newer inference code.

Each case runs in a child process with a 90-second limit. Default concurrency is one; `--workers` allows 1–5 (use two for the benchmark).
Worker process groups are terminated on timeout, including local Droid descendants.
An exclusive worktree lock prevents overlapping runs; append+fsync checkpoints
each result. Resume checks input/code/model hashes and rejects duplicates,
unknown IDs and changed labels. A crash-truncated final JSONL line is removed
before resuming; complete prior records are retained. Do not edit inference code
or merge while a run is active. Timeouts and failures remain visible in metrics.

## Offline artifact review

```bash
../HackHarvard/.venv/bin/python -m evals.audit_artifacts evals/runs/full-v2
../HackHarvard/.venv/bin/python -m evals.audit_screenshots evals/runs/full-v2
```

The script audit copies source as inert `.txt` and never executes it. The screenshot
audit copies existing local sandbox images, records dimensions and uniformity, and
never opens their URLs. A screenshot file can exist even when navigation failed.
The full-v2 evidence review samples the first case in each source/label stratum;
all claims in those seven cases are reviewed under the saved strict-grounding rubric.

## Chalk scoring and report artifacts

```bash
../HackHarvard/.venv/bin/python evals/chalk_score.py evals/runs/full-v2
MPLCONFIGDIR=/tmp/tripwire-matplotlib ../HackHarvard/.venv/bin/python -m evals.report evals/runs/full-v2
```

The Chalk command uploads inputs, labels and saved predictions, deploys a replay
task, and computes eight remote SQL scores. It does not call either model again.
It persists evaluation/run IDs and resumes an existing receipt on re-invocation.
Every remote row and score must agree with local calculations; a successful
run status alone is insufficient. First development upload predates the input
column addition; its inputs are separately preserved in `inputs.json`.

Report generation writes `evals/RESULTS.md`, `evals/results.csv` and
`evals/results_chart.png`. Additional plotting dependency is pinned in
`evals/requirements.txt`. Reports preserve development-only banners, unknown
costs, three-class confusion matrices, source strata, failures, and strict vs
warning false-positive rates. Review evidence items against actual message/check
outputs and save documented assessments as `<run>/evidence_review.json`; never
substitute evidence count or model confidence for correctness.

Final artifacts at `evals/RESULTS.md`, `results.csv` and `results_chart.png` use
`full-v3-baseline-headroom`, with real Chalk scores verified for all 240 rows.
Both systems reached 71.7% accuracy; see [INTERPRETATION.md](INTERPRETATION.md).
Development and interrupted outputs remain archived; do not substitute their scores.

## Baseline token-budget correction (final run slot)

Full-v2 finished with 27 incomplete baseline responses at a 128-token cap. A separate
invented URL returned a one-word label but consumed 109 completion tokens. The final
pass raises only the baseline cap to 1,024; the prompt, model and labels stay fixed.
All Tripwire predictions are reused unchanged, guarded by frozen source/input hashes.
This consumes slot 3/3, and is explicitly a post-hoc correction, not a fresh tool run.

```bash
../HackHarvard/.venv/bin/python -m evals.run --mode full --full-run --workers 2 \
  --out evals/runs/full-v3-baseline-headroom --reuse-tripwire evals/runs/full-v2 \
  --detonate-case url-69188 --detonate-case url-154131 --detonate-case synthetic-039
```

The selected detonation flags preserve input identity; no sandbox or Droid is called
again. Use the corrected output directory for Chalk scoring and final report generation.
Original full-v2 predictions and its report remain archived without replacement.

Final artifact regeneration (no inference or additional budget):

```bash
MPLCONFIGDIR=/tmp/tripwire-matplotlib ../HackHarvard/.venv/bin/python -m evals.report evals/runs/full-v3-baseline-headroom
# Re-read and verify the existing remote run; no new model calls:
../HackHarvard/.venv/bin/python evals/chalk_score.py evals/runs/full-v3-baseline-headroom
```
