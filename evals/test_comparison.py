import pytest

from evals.comparison import paired_outcomes, wilson


def test_wilson_boundaries_and_known_interval():
    assert wilson(0, 0) is None
    assert wilson(0, 60)[1] == pytest.approx(0.06017185)
    assert wilson(60, 60)[0] == pytest.approx(0.93982815)
    assert wilson(50, 100) == pytest.approx((0.40383153, 0.59616847))
    with pytest.raises(ValueError):
        wilson(2, 1)


def test_paired_correctness_counts_errors_as_failures():
    rows = []
    for i, (a, b) in enumerate([(True, True), (True, False), (False, True), (False, False)]):
        for system, correct in [("baseline", a), ("tripwire", b)]:
            rows.append(
                {
                    "case_id": str(i),
                    "system": system,
                    "label": "safe",
                    "prediction": "safe",
                    "error": None if correct else "timeout",
                }
            )
    assert paired_outcomes(rows) == {"both_correct": 1, "baseline_only": 1, "tripwire_only": 1, "neither_correct": 1}
    with pytest.raises(ValueError, match="Duplicate"):
        paired_outcomes(rows + [rows[0]])
    with pytest.raises(ValueError, match="Unpaired"):
        paired_outcomes(rows[:-1])
