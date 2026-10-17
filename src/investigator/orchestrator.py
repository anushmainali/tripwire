"""Investigation orchestrator: extract -> parallel checks (+ detonation, Droid) -> evidence-only verdict."""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait

from src.contracts import Entities, Evidence, IncomingMessage, Verdict
from src.investigator import verdict as verdict_mod
from src.investigator.checks.link import check_links
from src.investigator.checks.payment import check_payment
from src.investigator.checks.rdap import check_domain_age
from src.investigator.checks.script import check_script
from src.investigator.extract import extract
from src.investigator.safe_verify import safe_verify

log = logging.getLogger(__name__)

CHECK_TIMEOUT_S = 12.0
TOTAL_BUDGET_S = 85.0

# Optional heavier steps, registered by their modules so the orchestrator works without them.
# Each takes (msg, entities, evidence_so_far, case_dir_info) and returns (list[Evidence], extras dict).
Extra = Callable[[IncomingMessage, Entities, list[Evidence], dict], tuple[list[Evidence], dict]]
EXTRA_STEPS: dict[str, Extra] = {}


def _safe_run(name: str, fn, *args) -> list[Evidence]:
    try:
        return fn(*args)
    except Exception as error:  # noqa: BLE001 — a crashed check becomes a failed-check evidence item
        log.warning("check %s failed: %s", name, error)
        return [Evidence(name, f"The {name.replace('_', ' ')} check couldn't run", "info", ok=False)]


def run_checks(text: str, entities: Entities) -> tuple[list[Evidence], str | None]:
    script = check_script(text, entities)
    evidence = list(script.evidence) + check_links(entities)
    jobs = {"rdap_domain_age": (check_domain_age, entities.domains), "payment": (check_payment, entities)}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {name: pool.submit(_safe_run, name, fn, arg) for name, (fn, arg) in jobs.items()}
        wait(futures.values(), timeout=CHECK_TIMEOUT_S)
        for name, fut in futures.items():
            if fut.done():
                evidence += fut.result()
            else:
                evidence.append(Evidence(name, f"The {name.replace('_', ' ')} check timed out", "info", ok=False))
    return evidence, script.scam_type


def investigate(
    msg: IncomingMessage,
    context: str | None = None,
    use_llm: bool = True,
    steps: list[str] | None = None,
) -> Verdict:
    started = time.monotonic()
    entities = extract(msg.text)
    evidence, scam_type = run_checks(msg.text, entities)
    debug: dict = {"entities": entities.__dict__}
    screenshot = None
    note = ""
    for name in steps if steps is not None else list(EXTRA_STEPS):
        step = EXTRA_STEPS.get(name)
        if step is None:
            continue
        remaining = TOTAL_BUDGET_S - (time.monotonic() - started)
        if remaining < 10:
            note = "(Some checks were skipped to answer quickly.)"
            break
        try:
            extra_ev, extras = step(msg, entities, evidence, {"budget_s": remaining})
        except Exception as error:  # noqa: BLE001
            log.warning("step %s failed: %s", name, error)
            extra_ev, extras = [Evidence(name, f"The {name} step couldn't run", "info", ok=False)], {}
        evidence += extra_ev
        debug[name] = extras.get("debug")
        screenshot = screenshot or extras.get("screenshot_path")
        scam_type = scam_type or extras.get("scam_type")
    advice = safe_verify(entities.claimed_brand, scam_type)
    result = verdict_mod.build_verdict(msg.text, evidence, scam_type, advice, context, use_llm=use_llm, note=note)
    result.screenshot_path = screenshot
    result.debug.update(debug)
    result.debug["latency_s"] = round(time.monotonic() - started, 2)
    return result
