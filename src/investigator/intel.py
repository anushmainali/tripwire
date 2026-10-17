"""Community intel memory: indicators (domains, wallets, payment handles, phones) seen in past Tripwire verdicts.

Stores only indicator values, the verdict label and a salted hash of the reporter, never message text. Used live
(`intel=True`) so a new case can cite "flagged in N other checks"; off by default so eval runs can't contaminate
each other.
"""

import hashlib
import sqlite3
import threading
import time
from pathlib import Path

from src.config import ROOT
from src.contracts import Entities, Evidence
from src.investigator.checks.link import is_official
from src.investigator.extract import registrable_domain

DB_PATH = ROOT / "data" / "intel.db"
WINDOW_S = 30 * 86400
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db(path: Path | str = DB_PATH) -> sqlite3.Connection:
    global _conn
    if _conn is None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(path), check_same_thread=False)
        _conn.execute(
            "create table if not exists observations (indicator text, kind text, label text, reporter text, at real)"
        )
        _conn.execute("create index if not exists obs_ind on observations(indicator)")
    return _conn


def reset(path: Path | str = DB_PATH) -> None:
    global _conn
    with _lock:
        _conn = None
        _db(path)


def indicators(entities: Entities) -> list[tuple[str, str]]:
    out = [("domain", registrable_domain(d)) for d in entities.domains if not is_official(d)]
    out += [("wallet", a) for a in entities.crypto_addresses]
    out += [("handle", h.lower()) for h in entities.payment_handles]
    out += [("phone", p[-10:]) for p in entities.phones if len(p) >= 10]
    return list(dict.fromkeys(out))


def _reporter(sender: str) -> str:
    return hashlib.sha256(f"tripwire:{sender}".encode()).hexdigest()[:16]


def history(entities: Entities, sender: str) -> list[Evidence]:
    me = _reporter(sender)
    out: list[Evidence] = []
    with _lock:
        db = _db()
        for kind, value in indicators(entities)[:8]:
            rows = db.execute(
                "select label, count(distinct reporter) from observations "
                "where indicator = ? and reporter != ? and at > ? group by label",
                (value, me, time.time() - WINDOW_S),
            ).fetchall()
            counts = dict(rows)
            bad = counts.get("scam", 0) + counts.get("suspicious", 0)
            if bad:
                people = f"{bad} other {'person' if bad == 1 else 'people'}"
                sev = "red" if counts.get("scam", 0) >= 2 else "yellow"
                out.append(
                    Evidence("tripwire_history", f"This {kind} ({value}) was flagged in checks by {people}", sev)
                )
    return out


def record(entities: Entities, sender: str, label: str) -> None:
    me, now = _reporter(sender), time.time()
    with _lock:
        db = _db()
        db.executemany(
            "insert into observations values (?, ?, ?, ?, ?)",
            [(value, kind, label, me, now) for kind, value in indicators(entities)],
        )
        db.commit()
