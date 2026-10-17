"""Photon smoke test: reply once to a `ping` iMessage from PHOTON_TEST_SENDER.

Taken from Photon's "Build an iMessage agent" guide (Python tab):
https://photon.codes/docs/beta/get-started/imessage
The only change: keys load from .env (python-dotenv) instead of shell exports.

Run: .venv/bin/python -m smoke_tests.test_photon
Then, within 2 minutes, text exactly `ping` to PHOTON_AGENT_HANDLE from PHOTON_TEST_SENDER.
"""

from dotenv import load_dotenv

load_dotenv()

import os
import sys
import time
from datetime import datetime, timedelta, timezone

from photon_api import ApiError, Photon
from photon_api.generated.models import (
    EmailGroupContent,
    SendMessageRequest,
    SendTextContent,
    TextContent,
    UserSnapshot,
)
from photon_api.rpc_generated import ListMessagesInput, SendMessageHeader, SendMessageInput, SendMessagePath


def configuration():
    names = ("PHOTON_API_KEY", "PHOTON_PROJECT_ID", "PHOTON_PLATFORM", "PHOTON_AGENT_HANDLE", "PHOTON_TEST_SENDER")
    for name in names:
        if not os.environ.get(name):
            raise RuntimeError(f"Missing {name}.")
    key, project, platform, agent, sender = (os.environ[name] for name in names)
    if platform not in ("imessage", "email"):
        raise RuntimeError("PHOTON_PLATFORM must be imessage or email.")
    return dict(key=key, project=project, platform=platform, agent=agent, sender=sender)


def matches(item, c, started_at):
    # The client validates every response against the contract, so these checks
    # are the walkthrough's own rules: the right conversation, sender, and text.
    m = item.root.root
    if m.platform != c["platform"] or m.status != "received":
        return False
    if datetime.fromisoformat(m.createdAt) < started_at:
        return False
    if not isinstance(m.receivedBy, UserSnapshot):
        return False
    sender, agent, space = m.sentBy.root, m.receivedBy.root, m.space.root
    if sender.kind != "human" or sender.handle != c["sender"]:
        return False
    if agent.kind != "agent" or agent.handle != c["agent"] or sender.id == agent.id:
        return False
    if c["platform"] == "imessage" and space.kind != "direct":
        return False
    content = m.content
    if isinstance(content, TextContent):
        return content.format == "plain" and content.text.strip() == "ping"
    if c["platform"] != "email" or not isinstance(content, EmailGroupContent):
        return False
    plain = [p for p in (part.root for part in content.parts) if isinstance(p, TextContent) and p.format == "plain"]
    return len(plain) == 1 and plain[0].text.strip() == "ping"


def run(c, window_s=120.0, poll_s=2.0):
    started_at = datetime.now(timezone.utc)
    deadline = time.monotonic() + window_s
    created_since = (started_at - timedelta(seconds=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    with Photon(headers={"Authorization": f"Bearer {c['key']}"}) as photon:
        print("Ready. Waiting for the configured test sender.")
        while True:
            query = {"createdSince": created_since, "direction": "received", "order": "asc", "pageSize": 100, "platform": c["platform"]}
            while True:
                page = photon.projects.list_messages(
                    ListMessagesInput.model_validate({"path": {"id": c["project"]}, "query": query})
                )
                for item in page.items:
                    if not matches(item, c, started_at):
                        continue
                    m = item.root.root
                    photon.projects.send_message(
                        SendMessageInput(
                            path=SendMessagePath(id=c["project"]),
                            headers=SendMessageHeader.model_validate({"idempotency-key": f"first-agent-reply:{m.id}"}),
                            body=SendMessageRequest(
                                spaceId=m.space.root.id,
                                senderId=m.receivedBy.root.id,
                                parentMessageId=m.id,
                                content=SendTextContent(type="text", format="plain", text="Hello from your Photon agent!"),
                            ),
                        )
                    )
                    print("Reply accepted for asynchronous dispatch; delivery is not confirmed.")
                    return
                token = page.nextPageToken
                if not isinstance(token, str):
                    break
                query["pageToken"] = token
            if time.monotonic() + poll_s > deadline:
                raise RuntimeError("No matching ping found before the deadline.")
            time.sleep(poll_s)


if __name__ == "__main__":
    try:
        run(configuration())
    except ApiError as error:
        print(f"Photon API error {error.status} (request {error.request_id or 'unknown'}).", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
