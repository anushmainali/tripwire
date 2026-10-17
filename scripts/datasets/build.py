"""Build a frozen 120-case benchmark. Downloads only fixed UCI dataset archives.

Never visits any URL contained inside a dataset. Raw archives remain gitignored.
"""

import argparse
import csv
import hashlib
import io
import json
import random
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = {
    "sms": "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip",
    "urls": "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip",
}
FIELDS = ["case_id", "text", "label", "category", "source", "source_row", "synthetic", "rationale", "detonate"]
# Reviewed before any model predictions; UCI spam is not a fraud ground truth.
SMS_REVIEW = {
    189: ("scam", "Unsolicited guaranteed cash/prize award with a claim callback."),
    4002: ("scam", "Repeated-contact pressure and an unsolicited won-prize claim."),
    3964: ("scam", "Unsolicited award selection and closing-lines pressure."),
    66: ("scam", "Unsolicited bonus prize routed to a premium-rate claim number."),
    3808: ("scam", "Guaranteed prize, premium-rate callback and 12-hour deadline."),
    1119: ("scam", "Unsolicited cash award requiring premium-rate callback."),
    3006: ("scam", "Unsolicited ticket/cash award requiring premium-rate callback."),
    2730: ("scam", "Unsolicited cash/holiday collection with urgent premium-rate callback."),
    4282: ("scam", "Winner impersonation, premium-rate claim and 12-hour pressure."),
    3165: ("scam", "Repeated-contact pressure for unsolicited cash prize and paid callback."),
    3386: ("suspicious", "Unexpected billing-error/refund callback; cannot verify sender from text."),
    832: ("suspicious", "Secret-admirer bait with paid messages; deception not independently established."),
    3751: ("suspicious", "Unexpected voucher claim; insufficient context to establish fraud."),
    4451: ("suspicious", "Award language with disclosed charges; legitimacy unverified."),
    1197: ("suspicious", "Unexpected voicemail callback to nonstandard number; insufficient context."),
    3676: ("suspicious", "Contradictory won/enter-auction language; deceptive promotion suspected."),
    1208: ("suspicious", "Selected-bonus solicitation with disclosed paid messages."),
    1106: ("suspicious", "Carrier impersonation and surprise-link bait; site not inspected."),
    3434: ("suspicious", "Unexpected camera award claim; no independent proof of fraud."),
    2355: ("suspicious", "Urgent unspecified callback request without a verifiable sender."),
}

# Original, deliberately varied messages; no claim that these are observed real incidents.
SYNTHETIC = json.loads((Path(__file__).parent / "synthetic.json").read_text())


def archive(name: str, download: bool) -> zipfile.ZipFile:
    path = ROOT / "data" / "raw" / f"{name}.zip"
    if not path.exists():
        if not download:
            raise SystemExit(f"Missing {path.name}; run with --download (UCI archives only).")
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(ARCHIVES[name], timeout=45) as response:
            path.write_bytes(response.read(80_000_000))
    return zipfile.ZipFile(path)


def build(download: bool = False) -> list[dict]:
    rng = random.Random(20261017)
    rows = []

    def add(case_id, text, label, category, source, source_row, synthetic, rationale):
        rows.append(
            dict(
                zip(
                    FIELDS,
                    [
                        case_id,
                        text.strip(),
                        label,
                        category,
                        source,
                        source_row,
                        str(synthetic).lower(),
                        rationale,
                        "false",
                    ],
                    strict=True,
                )
            )
        )

    with archive("sms", download) as z:
        sms = [line.split("\t", 1) for line in z.read("SMSSpamCollection").decode("utf-8").splitlines()]
    # Deduplicate before sampling; preserve corpus row identifiers for reconstruction.
    ham = {}
    for i, (label, text) in enumerate(sms, 1):
        if label == "ham":
            ham.setdefault(text.strip(), i)
    for text, i in rng.sample(sorted(ham.items()), 20):
        add(
            f"sms-{i}",
            text,
            "safe",
            "sms_ham",
            "uci_sms",
            i,
            False,
            "UCI ham label; no independent authentication of sender.",
        )
    for i, (label, rationale) in SMS_REVIEW.items():
        assert sms[i - 1][0] == "spam"
        add(f"sms-{i}", sms[i - 1][1], label, "sms_spam_reviewed", "uci_sms", i, False, rationale)
    for i, (label, category, text, rationale) in enumerate(SYNTHETIC, 1):
        add(f"synthetic-{i:03}", text, label, category, "tripwire_synthetic", i, True, rationale)
    with archive("urls", download) as z:
        with z.open("PhiUSIIL_Phishing_URL_Dataset.csv") as raw:
            corpus = list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig")))
    for source_label, label in [("0", "scam"), ("1", "safe")]:
        unique = {}
        for i, row in enumerate(corpus, 1):
            if row["label"] == source_label:
                unique.setdefault(row["URL"].strip(), i)
        for url, i in rng.sample(sorted(unique.items()), 20):
            add(
                f"url-{i}",
                url,
                label,
                "url_only",
                "uci_phiusiil",
                i,
                False,
                f"Historical PhiUSIIL label {source_label} ({label}); current site status not verified.",
            )
    rng.shuffle(rows)
    assert len(rows) == 120 and len({r["text"] for r in rows}) == 120
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    rows = build(args.download)
    target = ROOT / "data" / "eval_set.csv"
    target.parent.mkdir(exist_ok=True)
    with target.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    # A tracked copy makes the exact frozen sample available without new downloads.
    frozen = ROOT / "evals" / "fixtures" / "eval_set.csv"
    frozen.parent.mkdir(parents=True, exist_ok=True)
    frozen.write_bytes(target.read_bytes())
    manifest = {
        "seed": 20261017,
        "cases": len(rows),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archives": {
            n: {"url": u, "sha256": hashlib.sha256((ROOT / "data" / "raw" / f"{n}.zip").read_bytes()).hexdigest()}
            for n, u in ARCHIVES.items()
        },
        "labels": {label: sum(r["label"] == label for r in rows) for label in ("safe", "scam", "suspicious")},
    }
    (frozen.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "archives"}, indent=2))


if __name__ == "__main__":
    main()
