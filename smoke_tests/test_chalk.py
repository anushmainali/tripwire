"""Chalk smoke test: one authenticated call (who-am-i).

Docs: https://docs.chalk.ai/docs/client-python and https://docs.chalk.ai/docs/online-authentication
Uses CHALK_CLIENT_ID/CHALK_CLIENT_SECRET from .env when set, otherwise your `chalk login` session.

Run: .venv/bin/python -m smoke_tests.test_chalk
"""

import sys

from chalk.client import ChalkClient

from src import config


def main() -> int:
    try:
        cfg = config.chalk()
        client = ChalkClient(
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            environment=cfg.environment,
            api_server=cfg.api_server,
        )
        print("Using service credentials from .env.")
    except config.ConfigError:
        # No service credentials: fall back to the `chalk login` session.
        client = ChalkClient()
        print("Using your `chalk login` session (no CHALK_CLIENT_ID/SECRET in .env).")
    me = client.whoami()
    # Print identifiers only, never credentials.
    print(f"user={me.user} environment_id={getattr(me, 'environment_id', None)} team_id={getattr(me, 'team_id', None)}")
    print("PASS: Chalk who-am-i call succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
