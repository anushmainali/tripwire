"""Per-sender thread state + message dedupe in SQLite (data/tripwire.db, gitignored)."""

import json
import sqlite3
import threading
import time
from dataclasses import asdict
from pathlib import Path

from src.config import ROOT
from src.contracts import Evidence, Verdict

DEFAULT_DB = ROOT / "data" / "tripwire.db"


class State:
    def __init__(self, path: Path | str = DEFAULT_DB):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(
                """
                create table if not exists seen (message_id text primary key, at real);
                create table if not exists threads (
                    sender text primary key, last_text text, context text, verdict text, updated_at real
                );
                """
            )

    def mark_seen(self, message_id: str) -> bool:
        """Record a message id. Returns False if it was already seen (so it must not be handled again)."""
        with self._lock:
            cur = self._db.execute("insert or ignore into seen values (?, ?)", (message_id, time.time()))
            self._db.commit()
            return cur.rowcount == 1

    def save_case(self, sender: str, text: str, verdict: Verdict, context: str | None = None) -> None:
        data = asdict(verdict)
        data["debug"] = {k: v for k, v in data.get("debug", {}).items() if k in ("latency_s", "deterministic")}
        with self._lock:
            self._db.execute(
                "insert or replace into threads values (?, ?, ?, ?, ?)",
                (sender, text, context, json.dumps(data, default=str), time.time()),
            )
            self._db.commit()

    def last_case(self, sender: str, max_age_s: float = 3600) -> tuple[str, str | None, Verdict] | None:
        with self._lock:
            row = self._db.execute(
                "select last_text, context, verdict, updated_at from threads where sender = ?", (sender,)
            ).fetchone()
        if not row or time.time() - row[3] > max_age_s:
            return None
        data = json.loads(row[2])
        data["evidence"] = [Evidence(**e) for e in data["evidence"]]
        return row[0], row[1], Verdict(**data)
