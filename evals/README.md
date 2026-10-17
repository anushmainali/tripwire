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
`full` includes Droid and requires the real integration. The runner currently
excludes detonation explicitly; this limitation must be disclosed until the
small sandbox sample is integrated. It never runs the Photon poller.

## Full benchmark (shared budget: at most 3 runs, 150 cases each)

Do not start until the integration development smoke and detonation review pass.
The full-run ledger is persisted **before** execution. Interrupted runs consume a
slot; resume them instead of starting another full run. Do not delete or reset
the ledger to bypass the budget.

```bash
../HackHarvard/.venv/bin/python -m evals.run --mode full --full-run --out evals/runs/full-v1
```

Each case runs in a child process with a 90-second limit. Runs are sequential.
An exclusive worktree lock prevents overlapping runs; append+fsync checkpoints
each result. Resume checks input/code/model hashes and rejects duplicates,
unknown IDs and changed labels. A crash-truncated final JSONL line is removed
before resuming; complete prior records are retained. Do not edit inference code
or merge while a run is active. Timeouts and failures remain visible in metrics.

## Chalk scoring and report artifacts

```bash
../HackHarvard/.venv/bin/python evals/chalk_score.py evals/runs/full-v1
MPLCONFIGDIR=/tmp/tripwire-matplotlib ../HackHarvard/.venv/bin/python -m evals.report evals/runs/full-v1
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

Current development artifacts intentionally do not claim a full benchmark win.
The failed initial gateway smoke remains in `dev-checks-v1` for diagnosis; use
`dev-checks-v2` for the corrected checks-only smoke and real remote scoring receipt.
