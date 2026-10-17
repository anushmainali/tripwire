"""Render verified saved predictions as Markdown, raw CSV, and a standalone PNG."""

import argparse
import csv
import json
from pathlib import Path

from evals.metrics import LABELS, grouped, summarize


def pct(value):
    return "N/A" if value is None else f"{100 * value:.1f}%"


def number(value):
    return "unknown" if value is None else f"{value:.3f}"


def report(run_dir: Path, destination: Path):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    rows = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text().splitlines()]
    from evals.run import validate_saved

    inputs = json.loads((run_dir / "inputs.json").read_text())
    validate_saved(rows, inputs)
    if len(inputs) != manifest["cases"]:
        raise ValueError("Input count does not match manifest")
    keys = {(r["case_id"], r["system"]) for r in rows}
    if len(keys) != len(rows) or len(rows) != 2 * manifest["cases"]:
        raise ValueError("Report requires complete, unique paired predictions")
    systems = {r["system"] for r in rows}
    if systems != {"baseline", "tripwire"}:
        raise ValueError("Expected baseline and tripwire")
    if {r["case_id"] for r in rows if r["system"] == "baseline"} != {
        r["case_id"] for r in rows if r["system"] == "tripwire"
    }:
        raise ValueError("Mismatched case IDs")
    metrics = grouped(rows)
    destination.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_id",
        "system",
        "label",
        "prediction",
        "source",
        "category",
        "latency_s",
        "model",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "error",
        "evidence",
        "safe_verify",
        "reply_text",
    ]
    with (destination / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "evidence": json.dumps(row.get("evidence", []), ensure_ascii=False)})
    final = manifest["full_run"] and manifest["mode"] == "full"
    status = "Frozen benchmark" if final else "DEVELOPMENT SMOKE — NOT THE BENCHMARK"
    lines = ["# Tripwire evaluation results", "", f"**{status}.**", ""]
    if not final:
        lines += [
            f"These {manifest['cases']} separate development messages validate integration only. "
            "They do not measure real-world scam detection or establish an advantage over the baseline.",
            "The frozen 120-case benchmark has not been run. "
            "Droid and detonation are absent from this checks ablation.",
            "",
        ]
    lines += [
        f"Run: `{run_dir.name}`. Code commit: `{manifest['git_sha']}`. Mode: `{manifest['mode']}`.",
        f"Created: {manifest['created_at']}. Baseline model: `{manifest['model']}`.",
        "Investigator model: its pinned source configuration (may differ from baseline; this is a system comparison).",
        "",
        "| Metric | Baseline | Tripwire |",
        "|---|---:|---:|",
    ]
    for title, key, fmt in [
        ("Cases", "n", str),
        ("Exact accuracy (failures incorrect)", "accuracy", pct),
        ("Scam precision", "scam_precision", pct),
        ("Scam recall", "scam_recall", pct),
        ("Strict false-positive rate", "false_positive_rate", pct),
        ("Warning false-positive rate", "warning_false_positive_rate", pct),
        ("Median latency (seconds)", "median_latency_s", number),
        ("Inference failures / fallbacks", "error_count", str),
        ("Failed evidence checks", "failed_check_count", str),
        ("Mean USD / case", "mean_cost_usd", number),
    ]:
        lines.append(f"| {title} | {fmt(metrics['baseline'][key])} | {fmt(metrics['tripwire'][key])} |")
    lines += [
        "",
        "Exact accuracy requires the correct three-class label and a successful call. Scam precision/recall "
        "treat only `scam` as positive. Strict FPR is scam predictions / gold-safe cases; warning FPR includes "
        "suspicious predictions. Missing denominators are N/A. Latency includes process startup and failures.",
        "Cost is **unknown**: the investigator does not expose complete billed token, Droid, and sandbox usage. "
        "Baseline token counts, when available, are retained in raw results; no price assumptions are substituted.",
        "",
    ]
    for system in sorted(systems):
        lines += [
            f"## {system.capitalize()} confusion matrix",
            "",
            "Gold rows; predicted columns, including fallbacks.",
            "",
            "| Gold | safe | suspicious | scam |",
            "|---|---:|---:|---:|",
        ]
        for gold in LABELS:
            counts = metrics[system]["confusion_matrix"][gold]
            lines.append(f"| {gold} | " + " | ".join(str(counts[p]) for p in LABELS) + " |")
        lines.append("")
    lines += ["## Source strata", "", "| Source | System | N | Accuracy | Warning FPR |", "|---|---|---:|---:|---:|"]
    for source in sorted({r["source"] for r in rows}):
        for system in sorted(systems):
            m = summarize([r for r in rows if r["source"] == source and r["system"] == system])
            lines.append(
                f"| {source} | {system} | {m['n']} | {pct(m['accuracy'])} | {pct(m['warning_false_positive_rate'])} |"
            )
    lines += ["", "## Evidence review", ""]
    review_path = run_dir / "evidence_review.json"
    if review_path.exists():
        review = json.loads(review_path.read_text())
        claims = review["claims"]
        supported = sum(c["assessment"] == "supported" for c in claims)
        lines += [
            f"Author spot-check: {supported}/{len(claims)} evidence items fully supported under a strict "
            "text/check-grounding rubric. This is an unblinded agent review, not independent expert validation.",
            review["summary"],
            "See the run's `evidence_review.json` for per-item support and limitations.",
        ]
    else:
        lines += [
            "Not yet reviewed. Nonempty evidence does not establish correctness; no correctness score is claimed."
        ]
    lines += ["", "## Chalk Evaluations", ""]
    receipt_path = run_dir / "chalk_receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        lines += [
            f"Evaluation ID: `{receipt['evaluation_id']}`. Run ID: `{receipt['run_id']}`.",
            f"Status: `{receipt['status']}`. Remote row/score verification: **{receipt.get('verified', False)}**.",
            "Systems ran locally; saved predictions were uploaded as a Chalk dataset. A deployed replay task "
            "returns each prediction, and eight remote SQL scorers measure correctness and confusion counts. "
            "Every returned output and score is checked against local calculations; task/scorer row errors "
            "invalidate verification even if the run status says SUCCEEDED.",
        ]
    else:
        lines += ["Pending; no remote evaluation success is claimed."]
    lines += [
        "",
        "## Reproduce and limitations",
        "",
        "```bash",
        "../HackHarvard/.venv/bin/python -m pytest tests evals -q",
        f"../HackHarvard/.venv/bin/python -m evals.report {run_dir} --out {destination}",
        "```",
        "",
        "See [DATASET.md](DATASET.md) for provenance, licenses, class policy, and historical-label limitations. "
        "Synthetic and selected cases are not representative of incoming scam prevalence. This benchmark "
        "does not evaluate Scamio, Norton, or another commercial system. Baseline and investigator have "
        "different prompts and potentially different models, so changes cannot be attributed to tools alone.",
        "",
        "![Baseline versus Tripwire](results_chart.png)",
        "",
    ]
    (destination / "RESULTS.md").write_text("\n".join(lines))
    chart(metrics, destination / "results_chart.png", status, manifest["cases"])


def chart(metrics, path: Path, status: str, count: int):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(11, 5.6), layout="constrained")
    names = ["Accuracy ↑", "Scam precision ↑", "Scam recall ↑", "Strict FPR ↓", "Warning FPR ↓"]
    keys = ["accuracy", "scam_precision", "scam_recall", "false_positive_rate", "warning_false_positive_rate"]
    x = np.arange(len(keys))
    for offset, system, color in [(-0.19, "baseline", "#627489"), (0.19, "tripwire", "#168779")]:
        values = [metrics[system][key] for key in keys]
        bars = ax.bar(
            x + offset, [0 if v is None else 100 * v for v in values], 0.36, label=system.capitalize(), color=color
        )
        ax.bar_label(bars, labels=["N/A" if v is None else f"{100 * v:.1f}%" for v in values], padding=4, fontsize=9)
    ax.set_xticks(x, names)
    ax.set_ylim(0, 113)
    ax.set_ylabel("Percent")
    ax.set_title(f"Tripwire · {status}\nn = {count} paired cases", loc="left", fontweight="bold", pad=18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("evals"))
    args = parser.parse_args()
    report(args.run_dir, args.out)
