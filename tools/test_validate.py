#!/usr/bin/env python3
"""Tests for tools/validate.py and tools/build_catalog.py. Standard library only.

    python tools/test_validate.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_catalog  # noqa: E402
import pngutil  # noqa: E402
import validate  # noqa: E402

FIXTURES = HERE / "fixtures"
REAL_PACKS = validate.REPO / "packs"

# fixture folder -> substring that must appear in at least one error (or warning, for "WARN:" rows)
BAD = {
    "bad-trademark-name": "trademark: pack.json name contains 'claude'",
    "bad-trademark-model-word": "contains 'sonnet'",
    "bad-script-in-json": "contains '<script'",
    "bad-banned-extension": ".exe files are banned",
    "bad-unlisted-file": "not listed in pack.json files",
    "bad-preview-too-wide": "limit is 4096 pixels",
    "bad-fake-png": "not a PNG",
    "bad-png-crc": "bad CRC",
    "bad-font-license": "font packs must use OFL-1.1 or Apache-2.0",
    "bad-font-magic": "not a TrueType/OpenType font",
    "bad-sprite-missing-anim": "required animation 'celebrate' is missing",
    "bad-sprite-grid": "not a whole number of 8x8 frames",
    "bad-sprite-index": "frame index 3 but the sheet has only 2 frames",
    "bad-sprite-stage-order": "must be greater than the previous stage",
    "bad-sprite-mood": "moods.exhausted names animation 'snore'",
    "bad-theme-missing-field": "accent is required",
    "bad-id-mismatch": "does not match the folder name",
    "bad-no-license": "LICENSE is missing",
    "bad-license-text": "LICENSE text does not look like MIT",
    "bad-effects-range": "period_ms must be an integer from 400 to 10000",
    "bad-palette-stops": "colors must be 1 to 4",
    "bad-pixel-char": "sheet.json: frames[0][3][3] is 'g'; a pixel is '.' (transparent) or 0-9, a-f",
    "bad-pixel-index": "frames[0][2][3] is palette index '3' (3) but the palette has only 3 colors",
    "bad-pixel-row-length": "frames[0][5] is 7 characters, expected 8 (frame_w)",
    "bad-pixel-rows": "frames[0] has 7 rows, expected 8 (frame_h)",
    "bad-pixel-frames": "animations use frame index 3 but the pixel sheet has only 3 frames",
    "bad-pixel-white": "palette[1] is pure white (#FFFFFF)",
    "bad-pixel-colors": "palette must be 1 to 16 #rrggbb colors (got 17)",
    "bad-pixel-frame-size": "frame_w and frame_h must be integers from 8 to 32, got 40 x 40",
    "bad-sprite-v1-json-sheet": "'sheet.json' is a .json pixel sheet, which needs sprite.json schema_version 2",
}

# issue #2 fixtures: each fails with exactly this one error line (after the pack label)
EXACT = {
    "bad-null-pack": "pack.json: must be a JSON object, got null",
    "bad-null-palettes": "palettes.json: must be a JSON object, got null",
    "bad-null-effects": "effects.json: must be a JSON object, got null",
    "bad-null-theme": "themes/fixture-dark.json: must be a JSON object, got null",
    "bad-null-sprite": "sprite.json: must be a JSON object, got null",
    "bad-null-pixel-sheet": "sheet.json: must be a JSON object, got null",
    "bad-newline-color": "palettes.json: palettes[0]: '#ff2a6d\\n' is not a #rrggbb color",
    "bad-newline-name": "palettes.json: palettes[0]: name must be 2 to 24 lowercase letters, digits or hyphens",
    "bad-newline-theme-color": "themes/fixture-dark.json: accent must be a #rrggbb color (six hex digits), "
                               "got '#ff2a6d\\n'",
    "bad-type-license": "pack.json: license [] is not allowed; use one of MIT, CC-BY-4.0, CC0-1.0, "
                        "Apache-2.0, OFL-1.1, BSD-3-Clause, ISC",
    "bad-type-sprite-files": "pack.json: files entries must be strings",
}
BAD.update(EXACT)

BUILT_INS = {
    "obsidian": {"name": "Obsidian", "bg": "#0d0d0d", "glass": "#1c1c1c", "glass_on_mica": "#1a1a1c",
                 "title_bg": "#161616", "border": "#333333", "text": "#e8e4dc", "text_secondary": "#b8b4ac",
                 "text_dim": "#777777", "text_muted": "#555555", "accent": "#6c63ff", "bar_bg": "#2a2a2a",
                 "footer_bg": "#111111", "pace_marker": "#ff6b6b", "sparkline": "#6c63ff",
                 "glass_alpha": 0.85, "border_alpha": 0.30, "border_tint": None,
                 "accent_bloom": {"blur": 4, "alpha": 0.35}, "inner_highlight": None},
    "aurora": {"name": "Aurora", "bg": "#0a0f1a", "glass": "#161e30", "glass_on_mica": "#141d2e",
               "title_bg": "#0f172a", "border": "#334155", "text": "#e2e8f0", "text_secondary": "#94a3b8",
               "text_dim": "#64748b", "text_muted": "#475569", "accent": "#38bdf8", "bar_bg": "#1e293b",
               "footer_bg": "#0c1220", "pace_marker": "#f472b6", "sparkline": "#38bdf8",
               "glass_alpha": 0.80, "border_alpha": 0.50, "border_tint": "#38bdf8",
               "accent_bloom": {"blur": 6, "alpha": 0.55}, "inner_highlight": {"color": "#38bdf8", "alpha": 0.20}},
    "ember": {"name": "Ember", "bg": "#1a0a0a", "glass": "#261414", "glass_on_mica": "#211010",
              "title_bg": "#1f0e0e", "border": "#442222", "text": "#f5e6e0", "text_secondary": "#d4a89c",
              "text_dim": "#8b6b60", "text_muted": "#6b4b40", "accent": "#f97316", "bar_bg": "#2d1a1a",
              "footer_bg": "#150808", "pace_marker": "#fbbf24", "sparkline": "#f97316",
              "glass_alpha": 0.82, "border_alpha": 0.40, "border_tint": "#f97316",
              "accent_bloom": {"blur": 6, "alpha": 0.55}, "inner_highlight": {"color": "#f97316", "alpha": 0.18}},
    "matrix": {"name": "Matrix", "bg": "#020a02", "glass": "#0a140a", "glass_on_mica": "#0a140a",
               "title_bg": "#040d04", "border": "#0f2a0f", "text": "#00ff41", "text_secondary": "#00cc33",
               "text_dim": "#00802b", "text_muted": "#005a1e", "accent": "#00ff41", "bar_bg": "#0a1a0a",
               "footer_bg": "#020802", "pace_marker": "#ff0040", "sparkline": "#00ff41",
               "glass_alpha": 1.0, "border_alpha": 0.50, "border_tint": "#00ff41",
               "accent_bloom": {"blur": 4, "alpha": 0.60}, "inner_highlight": None,
               "opts_out_of_mica": True, "monospace_font": "Cascadia Code",
               "monospace_fallback": "Consolas", "card_corner_radius": 2, "breath_period_ms": 1800},
}


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = validate.main(argv)
    return code, out.getvalue()


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sanduhr-widgets-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def copy_good(self, fixture, new_id=None):
        new_id = new_id or fixture
        dest = self.tmp / new_id
        shutil.copytree(FIXTURES / "good" / fixture, dest)
        if new_id != fixture:
            pj = json.loads((dest / "pack.json").read_text(encoding="utf-8"))
            pj["id"] = new_id
            (dest / "pack.json").write_text(json.dumps(pj, indent=2), encoding="utf-8")
        return dest

    def edit_json(self, path, fn):
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class GoodFixtures(unittest.TestCase):
    def test_every_good_fixture_passes_strict(self):
        folders = sorted(p for p in (FIXTURES / "good").iterdir() if p.is_dir())
        self.assertGreaterEqual(len(folders), 6)
        for f in folders:
            with self.subTest(pack=f.name):
                rep = validate.validate_pack(f)
                self.assertEqual(rep.errors, [])
                self.assertEqual(rep.warnings, [])


class BadFixtures(unittest.TestCase):
    def test_every_bad_fixture_fails_with_the_right_message(self):
        on_disk = {p.name for p in (FIXTURES / "bad").iterdir() if p.is_dir()}
        self.assertEqual(on_disk - set(BAD) - {"bad-theme-light-bg"}, set(),
                         "a bad fixture has no expectation in BAD")
        for name, needle in BAD.items():
            with self.subTest(pack=name):
                rep = validate.validate_pack(FIXTURES / "bad" / name)
                self.assertTrue(rep.errors, "expected errors for %s" % name)
                self.assertTrue(any(needle in e for e in rep.errors),
                                "no error containing %r in %r" % (needle, rep.errors))

    def test_issue_2_fixtures_fail_with_exactly_one_error(self):
        for name, msg in EXACT.items():
            with self.subTest(pack=name):
                rep = validate.validate_pack(FIXTURES / "bad" / name)
                self.assertEqual(rep.errors, [msg])
                self.assertEqual(rep.warnings, [])

    def test_light_theme_is_a_warning_and_fails_only_under_strict(self):
        pack = FIXTURES / "bad" / "bad-theme-light-bg"
        rep = validate.validate_pack(pack)
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("bg is light" in w for w in rep.warnings))
        self.assertEqual(run_main([str(pack)])[0], 0)
        self.assertEqual(run_main(["--strict", str(pack)])[0], 1)

    def test_trademark_error_is_clear(self):
        rep = validate.validate_pack(FIXTURES / "bad" / "bad-trademark-name")
        msg = rep.errors[0]
        self.assertIn("no Anthropic or Claude marks", msg)
        self.assertIn("model names as branding", msg)


class TrademarkRule(unittest.TestCase):
    def test_substrings_and_words(self):
        for text, hit in (("Claude", "claude"), ("my-ANTHROPIC-pack", "anthropic"),
                          ("Opus Neon", "opus"), ("the haiku pack", "haiku"),
                          ("sonnet-theme", "sonnet"), ("Fable Gold", "fable")):
            self.assertEqual(validate.find_trademark(text), hit, text)

    def test_ordinary_words_pass(self):
        for text in ("Hourglass", "OLED Neon", "magnopus-free", "Unfableish", "palette"):
            self.assertIsNone(validate.find_trademark(text), text)


class Mutations(TempCase):
    def validate(self, pack):
        return validate.validate_pack(pack)

    def test_duplicate_json_key(self):
        d = self.copy_good("good-palette")
        (d / "palettes.json").write_text(
            '{"schema_version": 1, "schema_version": 1, "palettes": []}', encoding="utf-8")
        self.assertTrue(any("duplicate key" in e for e in self.validate(d).errors))

    def test_bom_is_rejected(self):
        d = self.copy_good("good-palette")
        raw = (d / "palettes.json").read_bytes()
        (d / "palettes.json").write_bytes(b"\xef\xbb\xbf" + raw)
        self.assertTrue(any("byte-order mark" in e for e in self.validate(d).errors))

    def test_unknown_manifest_key(self):
        d = self.copy_good("good-palette")
        self.edit_json(d / "pack.json", lambda m: m.update(homepage="https://example.com"))
        self.assertTrue(any("unknown key 'homepage'" in e for e in self.validate(d).errors))

    def test_bad_version_and_id(self):
        d = self.copy_good("good-palette")
        self.edit_json(d / "pack.json", lambda m: m.update(version="1.0", id="Bad_Id"))
        errs = self.validate(d).errors
        self.assertTrue(any("version '1.0'" in e for e in errs))
        self.assertTrue(any("kebab-case" in e for e in errs))

    def test_description_too_long(self):
        d = self.copy_good("good-palette")
        self.edit_json(d / "pack.json", lambda m: m.update(description="x" * 201))
        self.assertTrue(any("description must be a string of 1 to 200" in e for e in self.validate(d).errors))

    def test_path_traversal_in_files(self):
        d = self.copy_good("good-palette")
        self.edit_json(d / "pack.json", lambda m: m["files"].append("../escape.json"))
        self.assertTrue(any("not a safe relative path" in e for e in self.validate(d).errors))

    def test_listed_file_missing(self):
        d = self.copy_good("good-palette")
        (d / "palettes.json").unlink()
        self.assertTrue(any("missing from the pack" in e for e in self.validate(d).errors))

    def test_svg_and_script_extensions_are_named(self):
        for ext in (".svg", ".js", ".html", ".ps1"):
            with self.subTest(ext=ext):
                d = self.copy_good("good-palette", "mut-" + ext.strip("."))
                (d / ("extra" + ext)).write_text("x", encoding="utf-8")
                self.assertTrue(any("%s files are banned" % ext in e for e in self.validate(d).errors))

    def test_unknown_extension_is_rejected(self):
        d = self.copy_good("good-palette")
        (d / "notes.txt").write_text("hello", encoding="utf-8")
        self.assertTrue(any("not allowed" in e for e in self.validate(d).errors))

    def test_executable_signature_in_data_file(self):
        d = self.copy_good("good-palette")
        (d / "palettes.json").write_bytes(b"MZ" + b"\x00" * 10)
        self.assertTrue(any("Windows executable" in e for e in self.validate(d).errors))

    def test_png_over_two_megabytes(self):
        d = self.copy_good("good-palette")
        self.edit_json(d / "pack.json", lambda m: m.update(preview="preview.png"))
        (d / "preview.png").write_bytes(pngutil.PNG_SIGNATURE + b"\x00" * (2 * 1024 * 1024 + 10))
        self.assertTrue(any("limit is 2 MB" in e for e in self.validate(d).errors))

    def test_png_with_trailing_data(self):
        d = self.copy_good("good-palette")
        self.edit_json(d / "pack.json", lambda m: m.update(preview="preview.png"))
        (d / "preview.png").write_bytes(pngutil.encode_rgba(2, 2, bytes(16)) + b"junk")
        self.assertTrue(any("trailing data" in e for e in self.validate(d).errors))

    def test_pack_over_ten_megabytes(self):
        d = self.copy_good("good-font")
        names = []
        for i in range(3):
            n = "big%d.ttf" % i
            (d / n).write_bytes(b"\x00\x01\x00\x00" + b"\x00" * (4 * 1024 * 1024))
            names.append(n)
        self.edit_json(d / "pack.json", lambda m: m["files"].extend(names))
        self.assertTrue(any("limit is 10 MB" in e for e in self.validate(d).errors))

    def test_symlink_is_rejected(self):
        d = self.copy_good("good-palette")
        try:
            os.symlink(str(d / "palettes.json"), str(d / "link.json"))
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("symlinks unavailable here")
        self.assertTrue(any("symlink" in e for e in self.validate(d).errors))

    def test_theme_text_color_must_be_a_hex(self):
        d = self.copy_good("good-theme")
        t = d / "themes" / "fixture-dark.json"
        self.edit_json(t, lambda m: m.update(text="white"))
        self.assertTrue(any("text must be a #rrggbb color" in e for e in self.validate(d).errors))

    def test_theme_unknown_key_is_an_error(self):
        d = self.copy_good("good-theme")
        self.edit_json(d / "themes" / "fixture-dark.json", lambda m: m.update(script="x"))
        self.assertTrue(any("unknown key 'script'" in e for e in self.validate(d).errors))

    def test_theme_dial_out_of_range(self):
        d = self.copy_good("good-theme")
        self.edit_json(d / "themes" / "fixture-dark.json", lambda m: m.update(glass_alpha=1.5))
        self.assertTrue(any("glass_alpha must be between" in e for e in self.validate(d).errors))

    def test_theme_file_name_pattern(self):
        d = self.copy_good("good-theme")
        shutil.move(str(d / "themes" / "fixture-dark.json"), str(d / "themes" / "Bad Name.json"))
        self.edit_json(d / "pack.json", lambda m: m.update(files=["themes/Bad Name.json"]))
        self.assertTrue(self.validate(d).errors)

    def test_sprite_requires_exactly_sheet_or_stages(self):
        d = self.copy_good("good-sprite")
        self.edit_json(d / "sprite.json", lambda s: s.update(
            stages=[{"id": "aa", "name": "A", "min_growth": 0, "sheet": "sprite.png",
                     "frame_w": 8, "frame_h": 8}]))
        self.assertTrue(any("exactly one of" in e for e in self.validate(d).errors))

    def test_sprite_first_stage_must_start_at_zero(self):
        d = self.copy_good("good-sprite-stages")
        self.edit_json(d / "sprite.json", lambda s: s["stages"][0].update(min_growth=0.2))
        self.assertTrue(any("first stage must have min_growth 0" in e for e in self.validate(d).errors))

    def test_sprite_stage_zero_matches_base_frame(self):
        d = self.copy_good("good-sprite-stages")
        self.edit_json(d / "sprite.json", lambda s: s.update(frame_w=16, frame_h=16))
        self.assertTrue(any("must equal the top-level" in e for e in self.validate(d).errors))

    def test_sprite_stage_sheet_must_be_listed(self):
        d = self.copy_good("good-sprite-stages")
        self.edit_json(d / "pack.json", lambda m: m["files"].remove("sprites/two.png"))
        errs = self.validate(d).errors
        self.assertTrue(any("must list sprites/two.png" in e for e in errs), errs)

    def test_sprite_trigger_names_must_exist(self):
        d = self.copy_good("good-sprite")
        self.edit_json(d / "sprite.json", lambda s: s["triggers"].update(idle="missing"))
        self.assertTrue(any("triggers.idle names animation 'missing'" in e for e in self.validate(d).errors))

    def test_sprite_roam_speed_range(self):
        d = self.copy_good("good-sprite")
        self.edit_json(d / "sprite.json", lambda s: s["roam"].update(speed_px_s=500))
        self.assertTrue(any("roam.speed_px_s" in e for e in self.validate(d).errors))

    def test_sprite_six_stage_limit(self):
        d = self.copy_good("good-sprite-stages")

        def seven(s):
            s["stages"] = [dict(s["stages"][0], id="st%d" % i, min_growth=i / 10.0) for i in range(7)]
        self.edit_json(d / "sprite.json", seven)
        self.assertTrue(any("1 to 6 entries" in e for e in self.validate(d).errors))

    def test_effects_color_must_be_hex_or_ink(self):
        d = self.copy_good("good-effects")
        self.edit_json(d / "effects.json", lambda e: e["effects"][0].update(color="red"))
        self.assertTrue(any('#rrggbb color or "ink"' in e for e in self.validate(d).errors))

    def test_effects_type_enum(self):
        d = self.copy_good("good-effects")
        self.edit_json(d / "effects.json", lambda e: e["effects"][0].update(type="explode"))
        self.assertTrue(any("type must be one of" in e for e in self.validate(d).errors))

    def test_booleans_are_not_numbers(self):
        d = self.copy_good("good-effects")
        self.edit_json(d / "effects.json", lambda e: e["effects"][0].update(intensity=True))
        self.assertTrue(any("intensity must be a number" in e for e in self.validate(d).errors))

    def test_duplicate_ids_across_paths(self):
        a = self.tmp / "a"
        b = self.tmp / "b"
        a.mkdir()
        b.mkdir()
        shutil.copytree(FIXTURES / "good" / "good-palette", a / "good-palette")
        shutil.copytree(FIXTURES / "good" / "good-palette", b / "good-palette")
        reports = validate.validate_paths([str(a), str(b)])
        self.assertTrue(any("already used" in e for r in reports for e in r.errors))


class PixelSheets(TempCase):
    """Sprite schema v2: .json pixel sheets (FORMAT 5.5)."""

    def errors(self, pack):
        return validate.validate_pack(pack).errors

    def test_bad_pixel_fixtures_fail_with_exactly_one_error(self):
        for name in BAD:
            if name.startswith("bad-pixel-") or name == "bad-sprite-v1-json-sheet":
                with self.subTest(pack=name):
                    self.assertEqual(len(self.errors(FIXTURES / "bad" / name)), 1)

    def test_v1_sprites_stay_valid_unchanged(self):
        for name in ("good-sprite", "good-sprite-stages"):
            s = json.loads((FIXTURES / "good" / name / "sprite.json").read_text(encoding="utf-8"))
            self.assertEqual(s["schema_version"], 1)
            self.assertEqual(self.errors(FIXTURES / "good" / name), [])

    def test_v2_with_png_sheets_only_is_valid(self):
        d = self.copy_good("good-sprite")
        self.edit_json(d / "sprite.json", lambda s: s.update(schema_version=2))
        self.assertEqual(self.errors(d), [])

    def test_schema_version_three_is_rejected(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "sprite.json", lambda s: s.update(schema_version=3))
        self.assertTrue(any("schema_version must be 1 or 2" in e for e in self.errors(d)))

    def test_pixel_frame_must_match_the_stage(self):
        d = self.copy_good("good-sprite-pixel-stages")
        self.edit_json(d / "sprites" / "one.json", lambda p: p.update(
            frame_w=16, frame_h=16, frames=[["0" * 16] * 16] * 4))
        errs = self.errors(d)
        self.assertTrue(any("frame size 16x16 does not match the stage 'one' frame size 8x8" in e
                            for e in errs), errs)

    def test_uppercase_index_is_rejected(self):
        d = self.copy_good("good-sprite-pixel")

        def upper(p):
            p["frames"][1][0] = "..0A00.."
        self.edit_json(d / "sheet.json", upper)
        self.assertTrue(any("frames[1][0][3] is 'A'" in e for e in self.errors(d)))

    def test_pixel_sheet_must_be_listed_and_counts_as_a_file(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "pack.json", lambda m: m["files"].remove("sheet.json"))
        errs = self.errors(d)
        self.assertTrue(any("must list sheet.json" in e for e in errs), errs)

    def test_pixel_sheet_unknown_key_and_trademark_scan(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "sheet.json", lambda p: p.update(title="Claude pet"))
        errs = self.errors(d)
        self.assertTrue(any("unknown keys ['title']" in e for e in errs), errs)
        self.assertTrue(any("trademark: sheet.json value" in e for e in errs), errs)

    def test_missing_keys_and_wrong_types(self):
        d = self.copy_good("good-sprite-pixel")
        (d / "sheet.json").write_text('{"palette": "#22d3ee", "frames": [["........"], 7]}',
                                      encoding="utf-8")
        errs = self.errors(d)
        for needle in ("missing required key 'frame_w'", "palette must be 1 to 16",
                       "frames[1] must be an array of strings"):
            self.assertTrue(any(needle in e for e in errs), (needle, errs))

    def test_sheet_must_be_png_or_json(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "sprite.json", lambda s: s.update(sheet="sheet.txt"))
        self.assertTrue(any("must be a .png sheet or a .json pixel sheet" in e for e in self.errors(d)))

    def test_sprite_json_cannot_be_its_own_sheet(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "sprite.json", lambda s: s.update(sheet="sprite.json"))
        self.assertTrue(any("must not be sprite.json itself" in e for e in self.errors(d)))

    def test_a_broken_sheet_does_not_flood_the_report(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "sheet.json", lambda p: p.update(frames=[["zzzzzzzz"] * 8] * 40))
        errs = self.errors(d)
        self.assertLessEqual(len(errs), validate.PIXEL_MAX_ERRORS + 1)
        self.assertIn("more errors in this pixel sheet are not shown", errs[-1])

    def test_frame_limit(self):
        d = self.copy_good("good-sprite-pixel")
        self.edit_json(d / "sheet.json", lambda p: p.update(frames=p["frames"] * 65))
        self.assertTrue(any("frames must be an array of 1 to 256" in e for e in self.errors(d)))


class ThemeLintCalibration(unittest.TestCase):
    def test_built_in_themes_lint_clean(self):
        for key, theme in BUILT_INS.items():
            with self.subTest(theme=key):
                errs, warns = validate.lint_theme(theme)
                self.assertEqual((errs, warns), ([], []))

    def test_opt_out_with_translucent_glass_is_flagged(self):
        t = dict(BUILT_INS["matrix"], opts_out_of_mica=True, glass_alpha=0.5)
        errs, warns = validate.lint_theme(t)
        self.assertEqual(errs, [])
        self.assertTrue(any("glass_alpha to 1.0" in w for w in warns))

    def test_pace_marker_hidden_on_green(self):
        t = dict(BUILT_INS["obsidian"], pace_marker="#4adf7f")
        _, warns = validate.lint_theme(t)
        self.assertTrue(any("pace_marker disappears" in w for w in warns))

    def test_text_ramp_must_darken(self):
        t = dict(BUILT_INS["obsidian"], text_dim="#eeeeee")
        _, warns = validate.lint_theme(t)
        self.assertTrue(any("text_dim is not darker" in w for w in warns))


class Hardening(TempCase):
    """Issue #2: null files, trailing newlines and wrong JSON types."""

    def test_patterns_reject_a_trailing_newline(self):
        ok = {"ID_RE": "good-id", "SEMVER_RE": "1.0.0", "HEX_RE": "#ff2a6d", "PATH_SEG_RE": "a.json",
              "PRESET_NAME_RE": "plain", "ANIM_NAME_RE": "walk"}
        for name, value in ok.items():
            pat = getattr(validate, name)
            with self.subTest(pattern=name):
                self.assertTrue(pat.fullmatch(value))
                self.assertIsNone(pat.fullmatch(value + "\n"))
        self.assertIsNone(validate.THEME_FILE_RE.fullmatch("themes/a.json\n"))
        self.assertFalse(validate.safe_rel_path("sprite.png\n"))
        self.assertFalse(validate.safe_rel_path("sprites\n/one.png"))

    def test_no_pattern_is_applied_with_match(self):
        src = (HERE / "validate.py").read_text(encoding="utf-8")
        self.assertNotIn("_RE.match(", src)

    def test_trailing_newline_in_other_values(self):
        pal = self.copy_good("good-palette")
        self.edit_json(pal / "palettes.json", lambda d: d["palettes"][0]["colors"].append("#abcdef\n"))
        self.assertTrue(any("not a #rrggbb color" in e for e in validate.validate_pack(pal).errors))
        eff = self.copy_good("good-effects")
        self.edit_json(eff / "effects.json", lambda d: d["effects"][0].update(color="#abcdef\n"))
        self.assertTrue(any("color must be" in e for e in validate.validate_pack(eff).errors))
        spr = self.copy_good("good-sprite-stages")
        self.edit_json(spr / "sprite.json", lambda d: d["stages"][0].update(id="one\n"))
        self.assertTrue(any("id must be kebab-case" in e for e in validate.validate_pack(spr).errors))

    def test_null_in_every_json_file_of_every_good_pack_is_an_error(self):
        for pack in sorted(p for p in (FIXTURES / "good").iterdir() if p.is_dir()):
            for f in sorted(pack.rglob("*.json")):
                rel = f.relative_to(pack).as_posix()
                with self.subTest(pack=pack.name, file=rel):
                    work = self.tmp / ("n-" + pack.name)
                    shutil.rmtree(work, True)
                    shutil.copytree(pack, work)
                    (work / rel).write_text("null\n", encoding="utf-8", newline="\n")
                    rep = validate.validate_pack(work)
                    self.assertTrue(any("must be a JSON object, got null" in e for e in rep.errors),
                                    rep.errors)

    def test_top_level_wrong_types_are_errors(self):
        for pack in sorted(p for p in (FIXTURES / "good").iterdir() if p.is_dir()):
            for f in sorted(pack.rglob("*.json")):
                rel = f.relative_to(pack).as_posix()
                for text in ("[]", "0", "true", '"s"', "[null]"):
                    with self.subTest(pack=pack.name, file=rel, text=text):
                        work = self.tmp / ("t-" + pack.name)
                        shutil.rmtree(work, True)
                        shutil.copytree(pack, work)
                        (work / rel).write_text(text, encoding="utf-8", newline="\n")
                        self.assertTrue(validate.validate_pack(work).errors)

    def test_no_wrong_type_raises(self):
        """Replace every node of every JSON file in every good pack with each wrong type; never raise."""
        junk = [None, [], {}, 0, 1.5, True, "", "x\n", [[]], [{}], {"a": 1}, [None]]

        def paths(node, prefix=()):
            yield prefix
            if isinstance(node, dict):
                for k, v in node.items():
                    yield from paths(v, prefix + (k,))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    yield from paths(v, prefix + (i,))

        def get(root, path):
            for k in path:
                root = root[k]
            return root

        def put(root, path, value):
            get(root, path[:-1])[path[-1]] = value

        runs = 0
        for pack in sorted(p for p in (FIXTURES / "good").iterdir() if p.is_dir()):
            work = self.tmp / ("f-" + pack.name)
            shutil.copytree(pack, work)
            for f in sorted(work.rglob("*.json")):
                original = json.loads(f.read_text(encoding="utf-8"))
                for path in paths(original):
                    if not path:
                        continue
                    values = list(junk)
                    if isinstance(get(original, path), str):
                        values.append(get(original, path) + "\n")  # a trailing newline
                    for value in values:
                        data = json.loads(json.dumps(original))
                        put(data, path, value)
                        f.write_text(json.dumps(data), encoding="utf-8", newline="\n")
                        try:
                            validate.validate_pack(work)
                        except Exception as e:  # noqa: BLE001
                            self.fail("%s %s %s <- %r raised %r" % (pack.name, f.name, path, value, e))
                        runs += 1
                f.write_text(json.dumps(original), encoding="utf-8", newline="\n")
        self.assertGreater(runs, 1000)


class RealPacks(unittest.TestCase):
    def test_real_packs_pass_strict(self):
        reports = validate.validate_paths([str(REAL_PACKS)])
        self.assertGreaterEqual(len(reports), 4)
        for rep in reports:
            with self.subTest(pack=rep.label):
                self.assertEqual(rep.errors, [])
                self.assertEqual(rep.warnings, [])

    def test_oled_theme_text_is_capped(self):
        for f in (REAL_PACKS / "oled-neon" / "themes").glob("*.json"):
            t = json.loads(f.read_text(encoding="utf-8"))
            for key in ("bg", "glass", "glass_on_mica", "title_bg", "footer_bg"):
                self.assertEqual(t[key], "#000000", f.name)
            for key in ("text", "text_secondary", "text_dim", "text_muted"):
                self.assertTrue(all(int(t[key][i:i + 2], 16) <= 0xE6 for i in (1, 3, 5)), (f.name, key))

    def test_hourglass_has_four_growing_stages_and_no_pure_white(self):
        pack = REAL_PACKS / "hourglass"
        s = json.loads((pack / "sprite.json").read_text(encoding="utf-8"))
        self.assertEqual([st["id"] for st in s["stages"]], ["egg", "sprout", "runner", "keeper"])
        growth = [st["min_growth"] for st in s["stages"]]
        self.assertEqual(growth, sorted(set(growth)))
        for png in list((pack / "sprites").glob("*.png")) + [pack / "preview.png"]:
            self.assertFalse(has_pure_white(png.read_bytes()), png.name)


def has_pure_white(png_bytes):
    """Decode a non-interlaced 8-bit RGBA PNG written by tools/pngutil.py and look for #ffffff."""
    import struct
    import zlib
    w, h = struct.unpack(">II", png_bytes[16:24])
    pos, idat = 8, b""
    while pos < len(png_bytes):
        ln, tag = struct.unpack(">I4s", png_bytes[pos:pos + 8])
        if tag == b"IDAT":
            idat += png_bytes[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = 1 + w * 4
    for y in range(h):
        row = raw[y * stride + 1:(y + 1) * stride]
        for x in range(w):
            r, g, b, a = row[x * 4:x * 4 + 4]
            if a and (r, g, b) == (255, 255, 255):
                return True
    return False


class Catalog(TempCase):
    def build(self, out, **kw):
        with contextlib.redirect_stderr(io.StringIO()):
            return build_catalog.build(REAL_PACKS, out, kw.get("tag", "v1.0.0"),
                                       "2026-01-01T00:00:00Z")

    def test_catalog_shape(self):
        cat = self.build(self.tmp / "dist")
        self.assertEqual(cat["schema_version"], 1)
        ids = [p["id"] for p in cat["packs"]]
        self.assertEqual(ids, sorted(ids))
        for p in cat["packs"]:
            self.assertEqual(set(p), {"id", "name", "kind", "version", "sanduhr_min", "url", "sha256", "size"})
            self.assertEqual(p["url"], "https://github.com/626Labs-LLC/sanduhr-widgets/releases/download/"
                                       "v1.0.0/%s-%s.zip" % (p["id"], p["version"]))
            self.assertRegex(p["sha256"], r"^[0-9a-f]{64}$")
            z = self.tmp / "dist" / ("%s-%s.zip" % (p["id"], p["version"]))
            self.assertEqual(z.stat().st_size, p["size"])
            self.assertEqual(build_catalog.sha256_of(z), p["sha256"])

    def test_catalog_file_is_lf_sorted_json(self):
        self.build(self.tmp / "dist")
        raw = (self.tmp / "dist" / "catalog.json").read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"}\n"))
        self.assertEqual(json.loads(raw)["generated_at"], "2026-01-01T00:00:00Z")

    def test_builds_are_reproducible(self):
        a = self.build(self.tmp / "one")
        b = self.build(self.tmp / "two")
        self.assertEqual(a, b)
        self.assertEqual((self.tmp / "one" / "catalog.json").read_bytes(),
                         (self.tmp / "two" / "catalog.json").read_bytes())

    def test_zip_contents(self):
        import zipfile
        self.build(self.tmp / "dist")
        with zipfile.ZipFile(self.tmp / "dist" / "hourglass-1.0.0.zip") as zf:
            names = zf.namelist()
            self.assertEqual(names, sorted(names))
            self.assertIn("pack.json", names)
            self.assertIn("sprites/keeper.png", names)
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in zf.infolist()))
            self.assertFalse(any(n.endswith("/") for n in names))

    def test_build_refuses_a_failing_pack(self):
        packs = self.tmp / "packs"
        shutil.copytree(FIXTURES / "bad" / "bad-trademark-name", packs / "bad-trademark-name")
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                build_catalog.build(packs, self.tmp / "dist", "v1.0.0")
        self.assertFalse((self.tmp / "dist" / "catalog.json").exists())


class Cli(unittest.TestCase):
    def test_exit_codes_and_one_line_per_finding(self):
        code, out = run_main([str(FIXTURES / "good" / "good-theme")])
        self.assertEqual(code, 0)
        code, out = run_main([str(FIXTURES / "bad" / "bad-trademark-name")])
        self.assertEqual(code, 1)
        lines = [l for l in out.splitlines() if l.startswith("ERROR")]
        self.assertEqual(len(lines), 1)

    def test_missing_path_fails(self):
        code, _ = run_main(["definitely-not-a-folder"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
