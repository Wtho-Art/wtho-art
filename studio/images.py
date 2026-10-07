"""Resize uploads to a GitHub-sized JPEG. Uses ImageMagick when it is installed."""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 40 * 1024 * 1024
MAX_EDGE = 2000
TARGET_BYTES = 1_500_000
MAX_OUTPUT_BYTES = 8_000_000
START_QUALITY = 82
FLOOR_QUALITY = 60
Image.MAX_IMAGE_PIXELS = 80_000_000

RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


class ImageError(Exception):
    pass


def magick_bin() -> str | None:
    for name in ("magick", "convert"):
        path = shutil.which(name)
        if not path:
            continue
        try:
            proc = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if "ImageMagick" in (proc.stdout + proc.stderr):
            return path
    return None


def magick_command(binary: str, source: Path, dest: Path, quality: int, resize: bool) -> list[str]:
    command = [binary, str(source), "-auto-orient", "-colorspace", "sRGB"]
    if resize:
        command.extend(["-resize", f"{MAX_EDGE}x{MAX_EDGE}>"])
    command.extend(
        [
            "-strip",
            "-interlace",
            "Plane",
            "-quality",
            str(quality),
            "-sampling-factor",
            "4:2:0",
            str(dest),
        ]
    )
    return command


def prepare_jpeg(data: bytes, encoder: str | None = None) -> bytes:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageError("Die Datei ist größer als 40 MB.")
    if not data:
        raise ImageError("Die Datei ist leer.")
    chosen = encoder if encoder is not None else ("magick" if magick_bin() else "pillow")
    if chosen == "magick":
        binary = magick_bin()
        if not binary:
            raise ImageError("ImageMagick ist nicht installiert.")
        return _prepare_magick(data, binary)
    if chosen != "pillow":
        raise ImageError("Unbekannter Bildwandler.")
    return _prepare_pillow(data)


def _prepare_pillow(data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            rgb = _to_rgb(image)
            rgb = _resize(rgb)
            return _encode_jpeg(rgb)
    except Image.DecompressionBombError as exc:
        raise ImageError("Das Bild ist zu groß.") from exc
    except Image.UnidentifiedImageError as exc:
        raise ImageError("Die Datei ist kein Bild.") from exc
    except OSError as exc:
        raise ImageError("Die Datei ist kein Bild.") from exc


def _to_rgb(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image) or image
    if "A" in image.mode:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _resize(image: Image.Image) -> Image.Image:
    width, height = image.size
    long_edge = max(width, height)
    if long_edge <= MAX_EDGE:
        return image
    scale = MAX_EDGE / long_edge
    return image.resize((max(1, round(width * scale)), max(1, round(height * scale))), RESAMPLE)


def _encode_jpeg(image: Image.Image, target_bytes: int = TARGET_BYTES) -> bytes:
    quality = START_QUALITY
    best = b""
    while quality >= FLOOR_QUALITY:
        buffer = io.BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=2,
        )
        best = buffer.getvalue()
        if len(best) <= target_bytes:
            break
        quality -= 5
    if len(best) > MAX_OUTPUT_BYTES:
        raise ImageError("Das Bild ist nach dem Verkleinern noch größer als 8 MB.")
    return best


def _prepare_magick(data: bytes, binary: str) -> bytes:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "in"
        dest = Path(directory) / "out.jpg"
        source.write_bytes(data)
        quality = START_QUALITY
        proc = subprocess.run(
            magick_command(binary, source, dest, quality, resize=True),
            capture_output=True,
        )
        if proc.returncode != 0 or not dest.is_file():
            raise ImageError("Die Datei ist kein Bild.")
        while dest.stat().st_size > TARGET_BYTES and quality > FLOOR_QUALITY:
            quality -= 5
            smaller = Path(directory) / "again.jpg"
            proc = subprocess.run(
                magick_command(binary, dest, smaller, quality, resize=False),
                capture_output=True,
            )
            if proc.returncode != 0 or not smaller.is_file():
                break
            smaller.replace(dest)
        result = dest.read_bytes()
    if len(result) > MAX_OUTPUT_BYTES:
        raise ImageError("Das Bild ist nach dem Verkleinern noch größer als 8 MB.")
    if not result.startswith(b"\xff\xd8"):
        raise ImageError("Die Datei ist kein Bild.")
    return result
