"""Investigation orchestrator: extract -> parallel checks (+ detonation, Droid) -> evidence-only verdict."""

import logging
import time
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
TOTAL_BUDGET_S = 85.0  # hard cap for the whole investigation (spec: answer within 90 s)
VERDICT_RESERVE_S = 18.0  # time kept back for the verdict LLM call
DETONATION_TIMEOUT_S = 60.0
ALL_STEPS = ("detonation", "droid")


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


def worth_deep_dive(entities: Entities, evidence: list[Evidence]) -> bool:
    """Run the Droid only when there's something to investigate (skips plain chit-chat for a fast reply)."""
    has_artifacts = any(
        (entities.urls, entities.crypto_addresses, entities.payment_handles, entities.phones, entities.emails)
    )
    return has_artifacts or any(e.severity in ("red", "yellow") for e in evidence)


def _detonation_target(entities: Entities) -> str | None:
    return entities.urls[0] if entities.urls else None


def investigate(
    msg: IncomingMessage,
    context: str | None = None,
    use_llm: bool = True,
    steps: tuple[str, ...] | list[str] | None = None,
) -> Verdict:
    """Full investigation. `steps` selects the heavy steps ("detonation", "droid"); [] = checks + verdict only."""
    from src.detonation.report import detonation_evidence
    from src.detonation.sandbox import detonate

    steps = ALL_STEPS if steps is None else steps
    started = time.monotonic()
    entities = extract(msg.text)
    pool = ThreadPoolExecutor(max_workers=2)
    url = _detonation_target(entities)
    det_future = pool.submit(detonate, url, DETONATION_TIMEOUT_S) if url and "detonation" in steps else None
    evidence, scam_type = run_checks(msg.text, entities)
    debug: dict = {"entities": entities.__dict__}
    note = ""

    def left(reserve: float = VERDICT_RESERVE_S) -> float:
        return TOTAL_BUDGET_S - (time.monotonic() - started) - reserve

    if "droid" in steps and worth_deep_dive(entities, evidence) and left() > 20:
        from src.investigator.droid_agent import droid_investigate

        remaining = left()
        try:
            droid_ev, extras = droid_investigate(msg, entities, evidence, det_future, timeout=min(75.0, remaining))
        except Exception as error:  # noqa: BLE001
            log.warning("droid step crashed: %s", error)
            droid_ev, extras = (
                [Evidence("droid_investigation", "The deep-investigation agent didn't finish", "info", ok=False)],
                {},
            )
        evidence += droid_ev
        debug["droid"] = extras.get("debug")
        scam_type = scam_type or extras.get("scam_type")
    screenshot = None
    if det_future is not None:
        try:
            det = det_future.result(timeout=max(1.0, left()))
            evidence += detonation_evidence(det, entities.claimed_brand)
            screenshot = det.screenshot_path
            debug["detonation"] = {k: v for k, v in det.__dict__.items() if k not in ("text_excerpt",)}
        except Exception as error:  # noqa: BLE001
            evidence.append(Evidence("detonation", "Opening the link in the sandbox timed out", "info", ok=False))
            debug["detonation"] = {"error": type(error).__name__}
            note = '(The link check is still running — reply "why" in a minute for details.)'
    pool.shutdown(wait=False, cancel_futures=True)
    advice = safe_verify(entities.claimed_brand, scam_type)
    result = verdict_mod.build_verdict(
        msg.text,
        evidence,
        scam_type,
        advice,
        context,
        use_llm=use_llm,
        note=note,
        has_links=bool(entities.urls),
        llm_timeout=max(8.0, left(reserve=0)),
    )
    result.screenshot_path = screenshot
    result.debug.update(debug)
    result.debug["latency_s"] = round(time.monotonic() - started, 2)
    return result
