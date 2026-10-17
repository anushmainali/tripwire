from PIL import Image, ImageDraw

from src.detonation.sandbox import valid_screenshot


def test_blank_rejected(tmp_path):
    p = tmp_path / "a.jpg"
    Image.new("RGB", (390, 844), "white").save(p)
    assert not valid_screenshot(p)


def test_content_accepted(tmp_path):
    p = tmp_path / "b.jpg"
    im = Image.new("RGB", (390, 844), "white")
    d = ImageDraw.Draw(im)
    for i in range(0, 800, 20):
        d.rectangle([20, i, 370, i + 10], fill=(i % 255, 40, 120))
    im.save(p, quality=95)
    assert valid_screenshot(p)


def test_missing_and_garbage(tmp_path):
    assert not valid_screenshot(None)
    g = tmp_path / "c.jpg"
    g.write_bytes(b"\xff\xd8" + b"x" * 6000)
    assert not valid_screenshot(g)
