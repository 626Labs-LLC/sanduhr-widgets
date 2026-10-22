"""Minimal PNG writer on the standard library (zlib + struct).

Dev-tool helper used by tools/art/draw_hourglass.py and the test fixtures.
It is not part of the pack format and is never shipped inside a pack.
"""
import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def encode_rgba(width, height, rgba):
    """Encode `rgba` (bytes, width*height*4) as an 8-bit RGBA PNG, deterministically."""
    if len(rgba) != width * height * 4:
        raise ValueError("pixel buffer does not match width*height*4")
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def write_rgba(path, width, height, rgba):
    with open(path, "wb") as fh:
        fh.write(encode_rgba(width, height, rgba))


def header_only_png(width, height):
    """A structurally valid PNG whose declared size is `width` x `height` but whose
    pixel data is a single compressed row of zeros repeated lazily. Only used to
    build 'too large' test fixtures cheaply (the IDAT is deflated zeros)."""
    stride = 1 + width * 4
    comp = zlib.compressobj(9)
    parts = []
    row = bytes(stride)
    for _ in range(height):
        parts.append(comp.compress(row))
    parts.append(comp.flush())
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", b"".join(parts))
        + _chunk(b"IEND", b"")
    )
