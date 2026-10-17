"""Photon iMessage channel: poll `projects.list_messages`, reply via `projects.send_message`.

Follows Photon's "Build an iMessage agent" guide (https://photon.codes/docs/beta/get-started/imessage).
On the shared line only plain messages into the same Space are allowed (no threaded replies).
"""

import json
import logging
import mimetypes
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from photon_api import ApiError, Photon
from photon_api.generated.models import (
    AttachmentContent,
    RootModel,
    SendAttachmentContent,
    SendMessageRequest,
    SendTextContent,
    TextContent,
    UserSnapshot,
)
from photon_api.rpc_generated import (
    DownloadAttachmentInput,
    GetAttachmentInput,
    ListMessagesInput,
    SendMessageHeader,
    SendMessageInput,
    SendMessagePath,
    UploadAttachmentHeader,
    UploadAttachmentInput,
    UploadAttachmentPath,
)

from src import config
from src.contracts import IncomingMessage

log = logging.getLogger(__name__)
MAX_TEXT = 3500


@dataclass
class ReplyTarget:
    space_id: str
    agent_id: str
    message_id: str


def _content_parts(content) -> tuple[str, list[str]]:
    """Text and attachment ids from a received message (plain text, a lone attachment, or a group of parts)."""
    parts = [p.root if hasattr(p, "root") else p for p in getattr(content, "parts", None) or [content]]
    texts = [p.text for p in parts if isinstance(p, TextContent)]
    attachments = [p.attachmentId for p in parts if isinstance(p, AttachmentContent)]
    return "\n".join(texts), attachments


def multipart_related(data: bytes, content_type: str, filename: str) -> tuple[bytes, str]:
    boundary = f"tripwire-{uuid.uuid4().hex}"
    meta = json.dumps({"contentType": content_type, "sizeBytes": len(data), "filename": filename}).encode()
    body = (
        f"--{boundary}\r\nContent-Type: application/json\r\n\r\n".encode()
        + meta
        + f"\r\n--{boundary}\r\nContent-Type: {content_type}\r\n\r\n".encode()
        + data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, f"multipart/related; boundary={boundary}"


class PhotonChannel:
    def __init__(self, cfg: config.PhotonConfig | None = None, lookback_s: float = 60.0):
        self.cfg = cfg or config.photon()
        self.client = Photon(headers={"Authorization": f"Bearer {self.cfg.api_key}"})
        since = datetime.now(UTC) - timedelta(seconds=lookback_s)
        self.created_since = since.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        self._send_counter: dict[str, int] = {}

    def close(self) -> None:
        self.client.close()

    def _accept(self, m) -> bool:
        if m.platform != self.cfg.platform or m.status != "received":
            return False
        if not isinstance(m.receivedBy, UserSnapshot):
            return False
        sender, agent, space = m.sentBy.root, m.receivedBy.root, m.space.root
        if sender.kind != "human" or agent.kind != "agent" or agent.handle != self.cfg.agent_handle:
            return False
        return not (self.cfg.platform == "imessage" and space.kind != "direct")

    def poll(self) -> list[tuple[IncomingMessage, ReplyTarget]]:
        out: list[tuple[IncomingMessage, ReplyTarget]] = []
        query = {
            "createdSince": self.created_since,
            "direction": "received",
            "order": "asc",
            "pageSize": 100,
            "platform": self.cfg.platform,
        }
        while True:
            page = self.client.projects.list_messages(
                ListMessagesInput.model_validate({"path": {"id": self.cfg.project_id}, "query": query})
            )
            for item in page.items:
                m = item.root.root
                if not self._accept(m):
                    continue
                text, attachments = _content_parts(m.content)
                msg = IncomingMessage(
                    message_id=m.id,
                    sender=m.sentBy.root.handle,
                    text=text,
                    space_id=m.space.root.id,
                    received_at=m.createdAt,
                    attachments=attachments,
                )
                out.append((msg, ReplyTarget(m.space.root.id, m.receivedBy.root.id, m.id)))
            token = page.nextPageToken
            if not isinstance(token, str):
                break
            query["pageToken"] = token
        return out

    def _idem(self, target: ReplyTarget, kind: str) -> str:
        key = f"{target.message_id}:{kind}"
        n = self._send_counter.get(key, 0)
        self._send_counter[key] = n + 1
        return f"tripwire:{key}:{n}"

    def _send(self, target: ReplyTarget, content, kind: str) -> None:
        req = SendMessageInput(
            path=SendMessagePath(id=self.cfg.project_id),
            headers=SendMessageHeader.model_validate({"idempotency-key": self._idem(target, kind)}),
            body=SendMessageRequest(spaceId=target.space_id, senderId=target.agent_id, content=content),
        )
        for attempt in range(3):
            try:
                self.client.projects.send_message(req)
                return
            except ApiError as error:
                if error.status == 429 or error.status >= 500:
                    wait = float(error.headers.get("retry-after", 2 * (attempt + 1)) or 2)
                    time.sleep(min(wait, 10))
                    continue
                raise

    def send_text(self, target: ReplyTarget, text: str) -> None:
        self._send(target, SendTextContent(type="text", format="plain", text=text[:MAX_TEXT]), "text")

    def fetch_attachment(self, attachment_id: str, max_bytes: int = 8_000_000) -> tuple[bytes, str] | None:
        """Download an incoming attachment. Returns (bytes, content type), or None if not an image / too big."""
        ids = {"id": self.cfg.project_id, "attachmentId": attachment_id}
        meta = self.client.projects.get_attachment(GetAttachmentInput.model_validate({"path": ids}))
        if not meta.contentType.startswith("image/") or meta.sizeBytes > max_bytes:
            return None
        data = self.client.projects.download_attachment(DownloadAttachmentInput.model_validate({"path": ids}))
        return data, meta.contentType

    def upload(self, path: str, key: str):
        """Upload a file. The API wants multipart/related: a JSON metadata part, then the file bytes."""
        data = Path(path).read_bytes()
        ctype = mimetypes.guess_type(path)[0] or "image/jpeg"
        body, content_type = multipart_related(data, ctype, Path(path).name)
        return self.client.projects.upload_attachment(
            UploadAttachmentInput(
                body=RootModel[bytes](body),
                path=UploadAttachmentPath(id=self.cfg.project_id),
                headers=UploadAttachmentHeader(
                    content_length=str(len(body)),
                    content_type=content_type,
                    idempotency_key=key,
                ),
            )
        )

    def send_image(self, target: ReplyTarget, path: str) -> bool:
        attachment = self.upload(path, f"tripwire-upload:{target.message_id}:{Path(path).parent.name}")
        for _ in range(6):  # attachment may need a moment before it's sendable (409 AttachmentNotReady)
            try:
                self._send(target, SendAttachmentContent(type="attachment", attachmentId=attachment.id), "image")
                return True
            except ApiError as error:
                if error.status == 409:
                    time.sleep(5)
                    continue
                raise
        return False
