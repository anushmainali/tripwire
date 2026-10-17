# Project name

_TBD: one-line tagline._

## The problem

_TBD: who has this problem, and why current solutions fall short._

## What it does

_TBD: the core user experience in two or three sentences._

## Demo

_TBD: demo video link, screenshots, or a sample iMessage conversation._

## How it works (architecture)

_TBD: architecture diagram and a walkthrough of the main components and data flow._

## How we use Factory Droid

_TBD: explain where and how Droid is used (Factory requires this section). Cover:_

- _Where Droid runs in the product (for example via the `droid-sdk` Python SDK in `src/`)._
- _What tasks we delegate to Droid, with what autonomy level and tools._
- _How Droid was used while building the project (CLI sessions, reviews, generated code)._

## How we use Chalk

_TBD: which features or queries we serve through Chalk, and why._

## How we use Photon

_TBD: how users reach the agent over iMessage via Photon, and what the agent does with messages._

## Evals and results

_TBD: what we measured, how (`evals/`), and the results._

## Setup and run

Requires Python 3.11+.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

Install the Droid CLI ([quickstart](https://docs.factory.com/droid-cli/quickstart)) and sign in by running `droid`, or set `FACTORY_API_KEY` in `.env`.

Check which settings are present (values are never printed):

```bash
.venv/bin/python -m src.config
```

Smoke tests, run from the repo root:

```bash
.venv/bin/python -m smoke_tests.test_droid
.venv/bin/python -m smoke_tests.test_chalk
.venv/bin/python -m smoke_tests.test_photon   # then text "ping" to your agent number
```

Lint:

```bash
.venv/bin/ruff check .
```

## Built at HackHarvard 2026

_TBD: team members and acknowledgements._

Licensed under the [MIT License](LICENSE).
