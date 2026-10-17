import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_frozen_dataset_provenance_and_balance():
    path = FIXTURES / "eval_set.csv"
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["sha256"]
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len({r["case_id"] for r in rows}) == len({r["text"] for r in rows}) == 120
    assert Counter(r["label"] for r in rows) == {"safe": 60, "scam": 50, "suspicious": 10}
    assert Counter(r["source"] for r in rows) == {"uci_sms": 40, "uci_phiusiil": 40, "tripwire_synthetic": 40}
    assert all(r["rationale"] and r["source_row"] and r["detonate"] == "false" for r in rows)
    assert sum(r["synthetic"] == "true" for r in rows) == 40
