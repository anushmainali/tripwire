"""Preserve Droid-generated Python as inert, reviewable benchmark evidence.

Never imports or executes scripts. Path and size guards prevent copying outside
case directories. AST flags are review hints, not a sandbox or proof of safety.
"""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

CASE_ROOT = Path("/tmp/tripwire-cases").resolve()
NETWORK_IMPORTS = {"socket", "urllib", "http", "httpx", "requests", "aiohttp", "ftplib", "subprocess", "webbrowser"}
SECRET_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN .*PRIVATE KEY-----)")


def analyze(source: str) -> list[str]:
    flags = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["parse_error"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            flags.update("review_import:" + n.name for n in node.names if n.name.split(".")[0] in NETWORK_IMPORTS)
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in NETWORK_IMPORTS:
            flags.add("review_import:" + node.module)
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name in ("eval", "exec", "__import__", "os.system", "os.popen", "os.getenv"):
                flags.add("review_call:" + name)
    return sorted(flags)


def collect(run_dir: Path) -> dict:
    rows = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text().splitlines()]
    artifacts = []
    for row in rows:
        if row["system"] != "tripwire":
            continue
        debug = row.get("debug", {}).get("droid") or {}
        if not debug.get("case_dir"):
            continue
        case_dir = Path(debug["case_dir"]).resolve()
        if not case_dir.is_relative_to(CASE_ROOT):
            raise ValueError("Droid case directory is outside approved artifact root")
        for script in sorted(case_dir.glob("*.py")):
            if not script.resolve().is_relative_to(case_dir) or script.stat().st_size > 100_000:
                raise ValueError("Unsafe artifact path or oversized script")
            source = script.read_text()
            if SECRET_PATTERN.search(source):
                raise ValueError("Possible secret in artifact; refusing to copy or print")
            # Case identifiers are dataset-controlled but still validate before building paths.
            case_id = row["case_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", case_id):
                raise ValueError("Unsafe case identifier")
            target = run_dir / "droid_artifacts" / case_id / (script.name + ".txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source)
            artifacts.append(
                {
                    "case_id": case_id,
                    "file": str(target.relative_to(run_dir)),
                    "sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "review_flags": analyze(source),
                }
            )
    result = {
        "method": "inert source capture and AST review hints; scripts are never executed by this audit",
        "scripts": artifacts,
        "script_cases": len({a["case_id"] for a in artifacts}),
        "flagged_scripts": sum(bool(a["review_flags"]) for a in artifacts),
    }
    (run_dir / "artifact_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = collect(args.run_dir)
    print(json.dumps({k: v for k, v in result.items() if k != "scripts"}, indent=2))
