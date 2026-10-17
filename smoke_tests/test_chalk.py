"""Chalk smoke test: one authenticated call (who-am-i).

Docs: https://docs.chalk.ai/docs/client-python and https://docs.chalk.ai/docs/online-authentication
ChalkClient reads CHALK_CLIENT_ID, CHALK_CLIENT_SECRET, CHALK_ENVIRONMENT and
(optionally) CHALK_API_SERVER from the environment; we load them from .env.

Run: .venv/bin/python -m smoke_tests.test_chalk
"""

import os
import sys

from chalk.client import ChalkClient
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    missing = [n for n in ("CHALK_CLIENT_ID", "CHALK_CLIENT_SECRET") if not os.environ.get(n)]
    if missing:
        print(f"FAIL: missing {', '.join(missing)} in .env.", file=sys.stderr)
        return 1
    # Empty optional values in .env would otherwise override the defaults.
    for name in ("CHALK_ENVIRONMENT", "CHALK_API_SERVER"):
        if not os.environ.get(name):
            os.environ.pop(name, None)

    me = ChalkClient().whoami()
    # Print identifiers only, never credentials.
    print(f"user={me.user} environment_id={getattr(me, 'environment_id', None)} team_id={getattr(me, 'team_id', None)}")
    print("PASS: Chalk who-am-i call succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
