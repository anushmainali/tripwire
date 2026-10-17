"""Inspect saved sandbox images offline; never navigate URLs or modify source images."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path("/tmp/tripwire-detonations").resolve()


def collect(run_dir: Path) -> list[dict]:
    records = []
    for line in (run_dir / "predictions.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["system"] != "tripwire" or not row.get("detonation_requested"):
            continue
        det = row.get("debug", {}).get("detonation") or {}
        record = {"case_id": row["case_id"], "capture_ok": det.get("ok", False), "status": det.get("status")}
        raw_path = row.get("screenshot_path")
        if not raw_path:
            record["image_error"] = "no_image_path"
        else:
            source = Path(raw_path).resolve()
            if not source.is_relative_to(ROOT) or not re.fullmatch(r"[A-Za-z0-9_-]+", row["case_id"]):
                raise ValueError("Unapproved screenshot path or case identifier")
            if not source.is_file():
                record["image_error"] = "file_missing"
            elif source.stat().st_size > 20_000_000:
                record["image_error"] = "file_too_large"
            else:
                try:
                    with Image.open(source) as image:
                        image.load()
                        stats = ImageStat.Stat(image.convert("RGB"))
                        record.update(
                            width=image.width,
                            height=image.height,
                            channel_stddev=stats.stddev,
                            uniform_image=max(stats.stddev) < 1.0,
                        )
                    target = run_dir / "sandbox_screenshots" / (row["case_id"] + source.suffix)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    record.update(
                        file=str(target.relative_to(run_dir)), sha256=hashlib.sha256(target.read_bytes()).hexdigest()
                    )
                except (OSError, ValueError):
                    record["image_error"] = "image_decode_failed"
        records.append(record)
    (run_dir / "screenshot_audit.json").write_text(json.dumps(records, indent=2) + "\n")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(collect(args.run_dir), indent=2))
