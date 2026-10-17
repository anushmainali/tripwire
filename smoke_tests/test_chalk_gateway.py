"""Chalk Model Gateway smoke test: one chat completion through the OpenAI client.

Docs: https://docs.chalk.ai/docs/model-gateway
Needs CHALK_ROUTER_API_KEY and CHALK_ENV_ID in .env (loaded via src/config.py).

Run: .venv/bin/python -m smoke_tests.test_chalk_gateway [model]
Without [model], it uses the first model the key can see (`chalk router model list`).
"""

import sys

from openai import APIStatusError, OpenAI

from src import config


def main() -> int:
    try:
        cfg = config.chalk_router()
    except config.ConfigError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    client = OpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        default_headers={"X-Chalk-Env-Id": cfg.env_id},
    )
    try:
        if len(sys.argv) > 1:
            model = sys.argv[1]
        else:
            models = [m.id for m in client.models.list()]
            if not models:
                print(
                    "FAIL: no models available to this key. Add a provider connection to the "
                    "Model Gateway in the Chalk dashboard, then check `chalk router model list`.",
                    file=sys.stderr,
                )
                return 1
            model = models[0]

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: pong"}],
        )
    except APIStatusError as error:
        # Status code only; the response body is not printed in case it echoes request headers.
        print(f"FAIL: Model Gateway returned HTTP {error.status_code}.", file=sys.stderr)
        return 1

    print(f"model={model} reply={resp.choices[0].message.content!r}")
    print("PASS: Chalk Model Gateway call succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
