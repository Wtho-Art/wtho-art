import io

from PIL import Image

import images


def _jpeg_with_orientation(wide, tall, orientation):
    image = Image.new("RGB", (wide, tall), (180, 20, 20))
    exif = image.getexif()
    exif[274] = orientation
    exif[270] = "SECRET-LOCATION"
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def test_shrinks_long_edge_and_strips_metadata():
    raw = _jpeg_with_orientation(2400, 1000, 1)
    out = images.prepare_jpeg(raw, encoder="pillow")
    assert out.startswith(b"\xff\xd8")
    with Image.open(io.BytesIO(out)) as result:
        assert result.size == (2000, 833)
        assert 270 not in result.getexif()
        assert result.getexif().get(274) in (None, 0, 1)


def test_exif_orientation_swaps_edges():
    raw = _jpeg_with_orientation(120, 40, 6)
    out = images.prepare_jpeg(raw, encoder="pillow")
    with Image.open(io.BytesIO(out)) as result:
        assert result.size == (40, 120)
        assert 270 not in result.getexif()


def test_small_image_is_not_enlarged():
    raw = _jpeg_with_orientation(80, 40, 1)
    out = images.prepare_jpeg(raw, encoder="pillow")
    with Image.open(io.BytesIO(out)) as result:
        assert result.size == (80, 40)


def test_png_becomes_jpeg_and_rejects_garbage():
    buffer = io.BytesIO()
    Image.new("RGB", (30, 10), (0, 0, 0)).save(buffer, format="PNG")
    out = images.prepare_jpeg(buffer.getvalue(), encoder="pillow")
    assert out.startswith(b"\xff\xd8")
    try:
        images.prepare_jpeg(b"not-an-image", encoder="pillow")
    except images.ImageError:
        pass
    else:
        raise AssertionError("garbage was accepted")


def test_quality_drops_for_noisy_pixels():
    image = Image.effect_noise((240, 240), 80).convert("RGB")
    high = images._encode_jpeg(image, target_bytes=10_000_000)
    low = images._encode_jpeg(image, target_bytes=1)
    assert low.startswith(b"\xff\xd8")
    assert len(low) < len(high)


def test_rejects_oversize_upload():
    try:
        images.prepare_jpeg(b"x" * (images.MAX_UPLOAD_BYTES + 1), encoder="pillow")
    except images.ImageError as exc:
        assert "40" in str(exc)
    else:
        raise AssertionError("oversize upload was accepted")


def test_magick_command_only_shrinks_and_strips():
    from pathlib import Path

    command = images.magick_command("magick", Path("in.jpg"), Path("out.jpg"), quality=82, resize=True)
    assert command[0] == "magick"
    assert "2000x2000>" in command
    assert "-strip" in command
    assert "--force" not in command
