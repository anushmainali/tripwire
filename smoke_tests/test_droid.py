"""Droid smoke test: have Droid write and run a small Python script on a sample CSV.

Run: .venv/bin/python -m smoke_tests.test_droid
Auth: an authenticated `droid` CLI session, or FACTORY_API_KEY in .env.
"""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from droid_sdk import Autonomy, SessionConfig, run
from pydantic import BaseModel

SAMPLE_CSV = Path(__file__).parent / "data" / "sample.csv"
EXPECTED = {"Boston": 95.33, "Phoenix": 22.33, "Seattle": 111.0}


class CityAverage(BaseModel):
    city: str
    average_rainfall_mm: float


class Result(BaseModel):
    script: str
    averages: list[CityAverage]


PROMPT = """\
There is a file sample.csv in the current directory with columns city, month, rainfall_mm.
Write a Python script named average_rainfall.py that uses only the standard library to
compute the average rainfall_mm per city, rounded to 2 decimals, and prints the results.
Run it with `python3 average_rainfall.py`, then return the script's source and the
averages it printed."""


async def main() -> int:
    load_dotenv()
    # Work in a throwaway directory so Droid never touches the repo.
    with tempfile.TemporaryDirectory(prefix="droid-smoke-") as workdir:
        shutil.copy(SAMPLE_CSV, workdir)
        result = await run(
            PROMPT,
            cwd=workdir,
            output=Result,
            timeout=300,
            # MEDIUM allows edits and reversible commands like running a script;
            # anything needing approval is rejected instead of hanging.
            config=SessionConfig(autonomy=Autonomy.MEDIUM, auto_reject_permission_requests=True),
        )
        ran_script = (Path(workdir) / "average_rainfall.py").exists()

    if not result.success:
        # Missing or invalid structured output also lands here (error_structured_output).
        print(f"FAIL: Droid run did not succeed ({result.subtype}).", file=sys.stderr)
        return 1
    output: Result = result.output  # guaranteed on success when output= is requested

    got = {a.city: round(a.average_rainfall_mm, 2) for a in output.averages}
    print("Script written by Droid:\n" + output.script)
    print(f"Averages: {got}")
    if not ran_script:
        print("FAIL: average_rainfall.py was not created.", file=sys.stderr)
        return 1
    if got != EXPECTED:
        print(f"FAIL: expected {EXPECTED}.", file=sys.stderr)
        return 1
    print("PASS: Droid wrote and ran the script with the correct result.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
