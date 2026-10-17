"""Descriptive uncertainty for the frozen convenience sample, with no model calls."""

from math import sqrt


def wilson(successes: int, total: int) -> tuple[float, float] | None:
    """95% Wilson interval; sampling assumptions do not make a convenience set representative."""
    if total < 0 or not 0 <= successes <= total:
        raise ValueError("Invalid binomial counts")
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0, center - margin), min(1, center + margin)


def paired_outcomes(rows: list[dict]) -> dict[str, int]:
    """Count paired successes, treating fallbacks as failures regardless of their label."""
    paired = {}
    for row in rows:
        case = paired.setdefault(row["case_id"], {})
        if row["system"] in case or row["system"] not in ("baseline", "tripwire"):
            raise ValueError("Duplicate or unknown system")
        case[row["system"]] = not row.get("error") and row["prediction"] == row["label"]
    counts = {"both_correct": 0, "baseline_only": 0, "tripwire_only": 0, "neither_correct": 0}
    for case in paired.values():
        if set(case) != {"baseline", "tripwire"}:
            raise ValueError("Unpaired case")
        a, b = case["baseline"], case["tripwire"]
        key = "both_correct" if a and b else "baseline_only" if a else "tripwire_only" if b else "neither_correct"
        counts[key] += 1
    return counts
