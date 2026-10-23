#!/usr/bin/env python3
"""Regenerate tools/fixtures/ (the good and bad packs that tools/test_validate.py checks).

Python 3, standard library only. The fixtures are committed; run this only when the format
changes:

    python tools/make_fixtures.py

Every bad fixture is one deliberate mistake away from a good one, named for the mistake.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pngutil  # noqa: E402

OUT = HERE / "fixtures"

MIT = ("MIT License\n\nCopyright (c) 2026 Fixture Author\n\nPermission is hereby granted, free of "
       "charge, to any person obtaining a copy of this software and associated documentation "
       "files, to deal in the Software without restriction.\n")
OFL = ("Copyright (c) 2026 Fixture Author\n\nThis Font Software is licensed under the SIL OPEN FONT "
       "LICENSE Version 1.1.\n")

THEME = {
    "name": "Fixture Dark", "bg": "#000000", "glass": "#000000", "glass_on_mica": "#000000",
    "title_bg": "#000000", "border": "#222222", "text": "#e6e6e6", "text_secondary": "#a8a8a8",
    "text_dim": "#707070", "text_muted": "#484848", "accent": "#ff2a6d", "bar_bg": "#141414",
    "footer_bg": "#000000", "pace_marker": "#ffd23f", "sparkline": "#ff2a6d",
    "glass_alpha": 1.0, "opts_out_of_mica": True,
}
PALETTES = {"schema_version": 1, "palettes": [
    {"name": "plain", "colors": ["#ff2a6d", "#05d9e8"], "mood": "test"}]}
EFFECTS = {"schema_version": 1, "effects": [
    {"name": "breathe", "type": "pulse", "intensity": 0.3, "period_ms": 4000, "color": "ink"}]}
SPRITE = {
    "schema_version": 1, "frame_w": 8, "frame_h": 8, "scale": 2, "fps": 8, "sheet": "sprite.png",
    "animations": {"walk": [0, 1], "sit": [0], "nap": [1], "pop": [2], "cheer": [3], "worry": [0],
                   "focus": [1], "sleep": [2], "celebrate": [3]},
    "moods": {"content": "sit", "focused": "focus", "worried": "worry", "exhausted": "sleep",
              "celebrate": "celebrate"},
    "triggers": {"needs_you": "pop", "job_passed": "cheer", "near_limit": "worry", "idle": "nap"},
    "roam": {"edges": ["bottom"], "speed_px_s": 20},
}

# Sprite v2 pixel sheet: four 8x8 frames (SPRITE's animations use indexes 0 to 3).
PIXEL_FRAME = ["..0000..", ".011110.", "01122110", "01122110", "01111110", ".011110.", "..0..0..", ".00..00."]
PIXEL = {
    "palette": ["#22d3ee", "#a855f7", "#ec4899"], "frame_w": 8, "frame_h": 8,
    "frames": [PIXEL_FRAME, PIXEL_FRAME[1:] + PIXEL_FRAME[:1], PIXEL_FRAME[::-1], PIXEL_FRAME],
}
SPRITE_V2 = dict(SPRITE, schema_version=2, sheet="sheet.json")


def pixel(**over):
    s = json.loads(json.dumps(PIXEL))
    s.update(over)
    return s


def manifest(pid, kind, files, **over):
    m = {"schema_version": 1, "id": pid, "name": "Fixture " + kind, "version": "1.0.0",
         "author": "Fixture Author", "license": "MIT", "kind": kind, "sanduhr_min": "3.8.0",
         "description": "A fixture pack for the validator tests.", "files": files}
    m.update(over)
    return m


def jw(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8", newline="\n")


def tw(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sheet(w, h):
    px = bytes([200, 140, 60, 255]) * (w * h)
    return pngutil.encode_rgba(w, h, px)


def bw(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def fake_font():
    return b"\x00\x01\x00\x00" + bytes(range(64))


def make(root, pid, kind, files, extra=None, lic=MIT, **over):
    d = root / pid
    jw(d / "pack.json", manifest(pid, kind, files, **over))
    tw(d / "LICENSE", lic)
    return d


def good(root):
    d = make(root, "good-theme", "theme", ["themes/fixture-dark.json"])
    jw(d / "themes" / "fixture-dark.json", THEME)
    d = make(root, "good-palette", "palette", ["palettes.json"])
    jw(d / "palettes.json", PALETTES)
    d = make(root, "good-effects", "effects", ["effects.json"])
    jw(d / "effects.json", EFFECTS)
    d = make(root, "good-font", "font", ["fixture.ttf"], lic=OFL, license="OFL-1.1")
    bw(d / "fixture.ttf", fake_font())
    d = make(root, "good-sprite", "sprite", ["sprite.json", "sprite.png"], preview="preview.png")
    jw(d / "sprite.json", SPRITE)
    bw(d / "sprite.png", sheet(32, 8))
    bw(d / "preview.png", sheet(16, 16))
    d = make(root, "good-sprite-stages", "sprite",
             ["sprite.json", "sprites/one.png", "sprites/two.png"])
    s = {k: v for k, v in SPRITE.items() if k != "sheet"}
    s["stages"] = [
        {"id": "one", "name": "One", "min_growth": 0, "sheet": "sprites/one.png", "frame_w": 8, "frame_h": 8},
        {"id": "two", "name": "Two", "min_growth": 0.5, "sheet": "sprites/two.png", "frame_w": 16, "frame_h": 16},
    ]
    jw(d / "sprite.json", s)
    bw(d / "sprites" / "one.png", sheet(32, 8))
    bw(d / "sprites" / "two.png", sheet(32, 32))
    d = make(root, "good-sprite-pixel", "sprite", ["sheet.json", "sprite.json"])
    jw(d / "sprite.json", SPRITE_V2)
    jw(d / "sheet.json", PIXEL)
    d = make(root, "good-sprite-pixel-stages", "sprite",
             ["sprite.json", "sprites/one.json", "sprites/two.png"])
    s = {k: v for k, v in SPRITE_V2.items() if k != "sheet"}
    s["stages"] = [
        {"id": "one", "name": "One", "min_growth": 0, "sheet": "sprites/one.json", "frame_w": 8, "frame_h": 8},
        {"id": "two", "name": "Two", "min_growth": 0.5, "sheet": "sprites/two.png", "frame_w": 16, "frame_h": 16},
    ]
    jw(d / "sprite.json", s)
    jw(d / "sprites" / "one.json", PIXEL)
    bw(d / "sprites" / "two.png", sheet(32, 32))


def bad(root):
    def palette(pid, **over):
        d = make(root, pid, "palette", ["palettes.json"], **over)
        jw(d / "palettes.json", PALETTES)
        return d

    palette("bad-trademark-name", name="Claude Neon")
    palette("bad-trademark-model-word", description="A pack that borrows the Sonnet name.")

    d = palette("bad-script-in-json")
    jw(d / "palettes.json", {"schema_version": 1, "palettes": [
        {"name": "plain", "colors": ["#ff2a6d"], "mood": "<script>x</script>"}]})

    d = make(root, "bad-banned-extension", "palette", ["palettes.json", "run.exe"])
    jw(d / "palettes.json", PALETTES)
    bw(d / "run.exe", b"MZ\x90\x00not really")

    d = palette("bad-unlisted-file")
    jw(d / "palettes-old.json", PALETTES)

    d = palette("bad-preview-too-wide", preview="preview.png")
    bw(d / "preview.png", pngutil.header_only_png(5000, 1))

    d = palette("bad-fake-png", preview="preview.png")
    bw(d / "preview.png", b"this is not a png at all")

    d = palette("bad-png-crc", preview="preview.png")
    data = bytearray(sheet(8, 8))
    data[20] ^= 0xFF  # corrupt IHDR payload, CRC no longer matches
    bw(d / "preview.png", bytes(data))

    d = make(root, "bad-font-license", "font", ["fixture.ttf"])
    bw(d / "fixture.ttf", fake_font())

    d = make(root, "bad-font-magic", "font", ["fixture.ttf"], lic=OFL, license="OFL-1.1")
    bw(d / "fixture.ttf", b"not a font " * 8)

    d = make(root, "bad-sprite-missing-anim", "sprite", ["sprite.json", "sprite.png"])
    s = json.loads(json.dumps(SPRITE))
    del s["animations"]["celebrate"]
    s["moods"]["celebrate"] = "cheer"
    jw(d / "sprite.json", s)
    bw(d / "sprite.png", sheet(32, 8))

    d = make(root, "bad-sprite-grid", "sprite", ["sprite.json", "sprite.png"])
    jw(d / "sprite.json", SPRITE)
    bw(d / "sprite.png", sheet(30, 8))

    d = make(root, "bad-sprite-index", "sprite", ["sprite.json", "sprite.png"])
    jw(d / "sprite.json", SPRITE)
    bw(d / "sprite.png", sheet(16, 8))  # two frames, animations use index 3

    d = make(root, "bad-sprite-stage-order", "sprite", ["sprite.json", "a.png", "b.png"])
    s = {k: v for k, v in SPRITE.items() if k != "sheet"}
    s["stages"] = [
        {"id": "aa", "name": "A", "min_growth": 0, "sheet": "a.png", "frame_w": 8, "frame_h": 8},
        {"id": "bb", "name": "B", "min_growth": 0, "sheet": "b.png", "frame_w": 8, "frame_h": 8},
    ]
    jw(d / "sprite.json", s)
    bw(d / "a.png", sheet(32, 8))
    bw(d / "b.png", sheet(32, 8))

    d = make(root, "bad-sprite-mood", "sprite", ["sprite.json", "sprite.png"])
    s = json.loads(json.dumps(SPRITE))
    s["moods"]["exhausted"] = "snore"
    jw(d / "sprite.json", s)
    bw(d / "sprite.png", sheet(32, 8))

    d = make(root, "bad-theme-missing-field", "theme", ["themes/fixture-dark.json"])
    t = {k: v for k, v in THEME.items() if k != "accent"}
    jw(d / "themes" / "fixture-dark.json", t)

    d = make(root, "bad-theme-light-bg", "theme", ["themes/fixture-light.json"])
    t = dict(THEME, bg="#f0f0f0", glass="#f0f0f0", glass_on_mica="#f0f0f0")
    jw(d / "themes" / "fixture-light.json", t)

    d = make(root, "bad-id-mismatch", "palette", ["palettes.json"], id="something-else")
    jw(d / "palettes.json", PALETTES)

    d = root / "bad-no-license"
    jw(d / "pack.json", manifest("bad-no-license", "palette", ["palettes.json"]))
    jw(d / "palettes.json", PALETTES)

    d = make(root, "bad-license-text", "palette", ["palettes.json"], lic="All rights reserved.\n")
    jw(d / "palettes.json", PALETTES)

    d = make(root, "bad-effects-range", "effects", ["effects.json"])
    jw(d / "effects.json", {"schema_version": 1, "effects": [
        {"name": "too-fast", "type": "pulse", "intensity": 0.3, "period_ms": 50, "color": "ink"}]})

    d = make(root, "bad-palette-stops", "palette", ["palettes.json"])
    jw(d / "palettes.json", {"schema_version": 1, "palettes": [
        {"name": "five", "colors": ["#111111"] * 5}]})

    # sprite v2 pixel sheets: each one mistake away from good-sprite-pixel
    def pixel_pack(pid, sheet_obj, sprite=SPRITE_V2):
        d = make(root, pid, "sprite", ["sheet.json", "sprite.json"])
        jw(d / "sprite.json", sprite)
        jw(d / "sheet.json", sheet_obj)

    f = list(PIXEL_FRAME)
    f[3] = "011g2110"
    pixel_pack("bad-pixel-char", pixel(frames=[f] + PIXEL["frames"][1:]))
    f = list(PIXEL_FRAME)
    f[2] = "01132110"  # index 3, palette has 3 colors (0 to 2)
    pixel_pack("bad-pixel-index", pixel(frames=[f] + PIXEL["frames"][1:]))
    f = list(PIXEL_FRAME)
    f[5] = ".01111."
    pixel_pack("bad-pixel-row-length", pixel(frames=[f] + PIXEL["frames"][1:]))
    pixel_pack("bad-pixel-rows", pixel(frames=[PIXEL_FRAME[:7]] + PIXEL["frames"][1:]))
    pixel_pack("bad-pixel-frames", pixel(frames=PIXEL["frames"][:3]))
    pixel_pack("bad-pixel-white", pixel(palette=["#22d3ee", "#FFFFFF", "#ec4899"]))
    pixel_pack("bad-pixel-colors", pixel(palette=["#%02x2040" % (i * 8) for i in range(17)]))
    big = ["." * 40] * 40
    pixel_pack("bad-pixel-frame-size", pixel(frame_w=40, frame_h=40, frames=[big] * 4),
               sprite=dict(SPRITE_V2, frame_w=40, frame_h=40))
    pixel_pack("bad-sprite-v1-json-sheet", PIXEL, sprite=dict(SPRITE_V2, schema_version=1))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    good(OUT / "good")
    bad(OUT / "bad")
    print("wrote fixtures under %s" % OUT)


if __name__ == "__main__":
    main()
