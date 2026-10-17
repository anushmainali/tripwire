import json

from src.channels.photon import multipart_related


def test_multipart_related_layout():
    body, ctype = multipart_related(b"\xff\xd8abc", "image/jpeg", "shot.jpg")
    boundary = ctype.split("boundary=")[1]
    parts = body.split(f"--{boundary}".encode())
    assert parts[0] == b"" and parts[-1] == b"--\r\n"
    meta = json.loads(parts[1].split(b"\r\n\r\n", 1)[1].strip())
    assert meta == {"contentType": "image/jpeg", "sizeBytes": 5, "filename": "shot.jpg"}
    assert parts[2].split(b"\r\n\r\n", 1)[1] == b"\xff\xd8abc\r\n"


def test_content_parts():
    from photon_api.generated.models import AttachmentContent, TextContent

    from src.channels.photon import _content_parts

    assert _content_parts(TextContent(type="text", format="plain", text="hi")) == ("hi", [])
    assert _content_parts(AttachmentContent(type="attachment", attachmentId="a1")) == ("", ["a1"])
