"""Chalk smoke test: one authenticated call (who-am-i).

Docs: https://docs.chalk.ai/docs/client-python and https://docs.chalk.ai/docs/online-authentication
Credentials come from .env via src/config.py.

Run: .venv/bin/python -m smoke_tests.test_chalk
"""

import sys

from chalk.client import ChalkClient

from src import config


def main() -> int:
    try:
        cfg = config.chalk()
    except config.ConfigError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    client = ChalkClient(
        client_id=cfg.client_id,
        client_secret=cfg.client_secret,
        environment=cfg.environment,
        api_server=cfg.api_server,
    )
    me = client.whoami()
    # Print identifiers only, never credentials.
    print(f"user={me.user} environment_id={getattr(me, 'environment_id', None)} team_id={getattr(me, 'team_id', None)}")
    print("PASS: Chalk who-am-i call succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
