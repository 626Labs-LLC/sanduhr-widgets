# Widget pack format, version 1

This file is authoritative. `tools/validate.py` implements it, `schema/*.json` restates the JSON
shapes for external tooling, and Sanduhr 3.8 re-validates every pack with the same rules before it
installs one. If this file and a tool disagree, the file wins and the tool has a bug.

Format v1 is **data only**. A pack carries JSON and PNG (and, for fonts, TTF/OTF). It never carries
code. There is no scripting hook in v1 and none is planned.

## 1. Pack layout

A pack is a folder `packs/<id>/` containing `pack.json`, a `LICENSE`, and its assets:

```
packs/<id>/
  pack.json        required
  LICENSE          required, the pack's own license text
  preview.png      optional, declared in pack.json "preview"
  <assets...>      every other file, each listed in pack.json "files"
```

The folder name must equal the pack `id`. Everything else is described by `pack.json`.

## 2. pack.json

UTF-8 JSON without a byte-order mark. Duplicate keys are an error. Unknown keys are an error.

| Key | Type | Rule |
|---|---|---|
| `schema_version` | integer | Must be `1`. |
| `id` | string | Lowercase kebab-case, 3 to 40 characters, `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, unique across the catalog, equal to the folder name. |
| `name` | string | 1 to 40 characters. |
| `version` | string | Semantic version `MAJOR.MINOR.PATCH`, no pre-release or build suffix. |
| `author` | string | 1 to 80 characters. |
| `license` | string | An SPDX identifier from the allowed list (section 4). |
| `kind` | string | `theme`, `palette`, `effects`, `font` or `sprite`. |
| `sanduhr_min` | string | Minimum Sanduhr version, `MAJOR.MINOR.PATCH`, for example `"3.8.0"`. |
| `description` | string | 1 to 200 characters. |
| `files` | array of strings | Every asset in the pack, relative POSIX paths, no duplicates, at most 64. Excludes `pack.json`, `LICENSE` and the `preview` file. |
| `preview` | string, optional | Path of a PNG preview. Not repeated in `files`. |

File listing is exact: the set of files on disk, minus `pack.json`, `LICENSE` and the `preview`
file, must equal `files`. An unlisted file is an error and so is a listed file that is missing.

No control characters are allowed in any string value.

## 3. Hard rules

These apply to every kind. A pack that breaks one is rejected by CI and by the client.

1. **Data only.** No scripts, executables, HTML, or SVG. The only file extensions allowed are
   `.json`, `.png`, `.ttf`, `.otf`, plus the extensionless `LICENSE`. The validator also names
   the usual suspects explicitly (`.exe .dll .bat .cmd .ps1 .sh .js .mjs .py .html .htm .svg .jar
   .msi .lnk .vbs .com .scr`) so the error says what it is. Text files are scanned for `<script`,
   `javascript:`, `<iframe` and `<!doctype html`. Executable signatures (`MZ`, ELF, `#!`) are
   rejected in any file.
2. **Images are PNG only**, checked by signature and by parsing the chunk stream (CRCs included).
   Each image is at most 2 MB and at most 4096 pixels on a side.
3. **Fonts are TTF or OTF only**, checked by magic number (`00 01 00 00`, `true`, or `OTTO`; font
   collections are rejected), at most 5 MB each, and the pack license must be `OFL-1.1` or
   `Apache-2.0`.
4. **Total size** of a pack is at most 10 MB.
5. **No symlinks, no hard-to-reason paths.** Paths in `files` and `preview` are relative, use `/`,
   and every segment matches `[A-Za-z0-9][A-Za-z0-9._-]*`. No `..`, no absolute paths, no drive
   letters, no backslashes, no spaces.
6. **No third-party trademarks or logos.** This explicitly includes **Anthropic and Claude marks
   and model names used as branding**. The validator rejects `claude` and `anthropic` anywhere,
   and `opus`, `sonnet`, `haiku` and `fable` as whole words, case-insensitively, in the pack `id`,
   `name`, `description`, `author`, every string value in the pack's JSON files, and every file
   name. Original art only: do not trace, recolor or imitate a studio's characters, a brand's
   logo, or a game's sprites.
7. **UTF-8 JSON** for every `.json` file.
8. At most 64 files per pack.

## 4. Licenses

`license` is an SPDX identifier. Allowed: `MIT`, `CC-BY-4.0`, `CC0-1.0`, `Apache-2.0`,
`OFL-1.1`, `BSD-3-Clause`, `ISC`. The pack folder must contain a non-empty `LICENSE` file (at
most 100 KB) whose text matches the declared license (the validator looks for the license's
well-known title or opening phrase). Kind `font` is limited to `OFL-1.1` and `Apache-2.0`.

The repository's own tooling is MIT (`/LICENSE`). Each pack carries its own license; contributing
a pack does not relicense anything else.

## 5. Kinds

### 5.1 `theme`

`files`: one to eight files, each `themes/<name>.json` with `<name>` lowercase kebab-case.
Nothing else.

Each file is a Sanduhr widget theme, the same JSON the in-app theme paste box, the drop-in themes
folder and the Theme Studio accept. It mirrors `ThemeModel.cs` and `ThemeLint.cs` in the Sanduhr
repository exactly.

Required fields, all `#rrggbb` except `name`:

`name` (string, 1 to 24 characters; the theme strip shows the first 12), `bg`, `glass`,
`glass_on_mica`, `title_bg`, `border`, `text`, `text_secondary`, `text_dim`, `text_muted`,
`accent`, `bar_bg`, `footer_bg`, `pace_marker`, `sparkline`.

Optional fields:

| Field | Type | Range |
|---|---|---|
| `glass_alpha` | number | 0 to 1 (default 0.80) |
| `border_alpha` | number | 0 to 1 (default 0.40) |
| `border_tint` | `#rrggbb` or `null` | |
| `accent_bloom` | `{ "blur": 0-20, "alpha": 0-1 }` | default `{4, 0.45}` |
| `inner_highlight` | `{ "color": "#rrggbb", "alpha": 0-1 }` or `null` | |
| `card_corner_radius` | number | 0 to 24 |
| `breath_period_ms` | number | 500 to 20000 |
| `opts_out_of_mica` | boolean | when true, set `glass_alpha` to 1.0 |
| `bg_grid` | boolean | |
| `monospace_font`, `monospace_fallback` | string | font family names |

No other keys are allowed in a catalog theme. Schema errors (missing field, malformed color, dial
out of range) fail the pack. The linter's design rules are measured the same way Sanduhr measures
them (dark base, text contrast over the composited card, a monochrome decreasing text ramp, a pace
marker that stands out on the bar fills, one accent hue). They are warnings in the app and
**errors in the catalog**: `tools/validate.py --strict` fails on them, and CI runs strict.

### 5.2 `palette`

`files`: exactly `["palettes.json"]`.

```json
{
  "schema_version": 1,
  "palettes": [
    { "name": "synthwave", "colors": ["#ff2a6d", "#d16ba5", "#05d9e8"], "mood": "neon night" }
  ]
}
```

1 to 64 entries. `name`: lowercase letters, digits and hyphens, 2 to 24 characters, unique in
the file. `colors`: 1 to 4 `#rrggbb` stops, interpolated left to right. `mood`: optional string,
at most 24 characters.

### 5.3 `effects`

`files`: exactly `["effects.json"]`.

```json
{
  "schema_version": 1,
  "effects": [
    { "name": "breathe", "type": "pulse", "intensity": 0.35, "period_ms": 4000, "color": "ink" }
  ]
}
```

1 to 64 presets. `name` as for palettes. `type`: `glow`, `sweep`, `shimmer` or `pulse`.
`intensity`: number 0 to 1. `period_ms`: integer 400 to 10000. `color`: `#rrggbb` or the literal
`"ink"`, which means the active theme's `text` color.

### 5.4 `font`

`files`: one to four `.ttf` or `.otf` files in the pack root or under `fonts/`. The pack license
must be `OFL-1.1` or `Apache-2.0` and `LICENSE` must carry the full license text. Families keep
their original names under OFL reserved-name rules; do not ship a modified font under the original
name.

### 5.5 `sprite`

A Desk companion. Art plus a mapping; Sanduhr supplies the behaviour (section 6).

`files`: `sprite.json` plus every sheet it references, and nothing else.

`sprite.json` has two schema versions. **Version 1** sheets are PNG only. **Version 2** is version
1 plus one more sheet type, the `.json` pixel sheet (below), so art can be written as data; every
other rule is identical, and a version 1 file stays valid unchanged.

```json
{
  "schema_version": 1,
  "frame_w": 32,
  "frame_h": 32,
  "scale": 2,
  "fps": 8,
  "stages": [
    { "id": "egg", "name": "Egg", "min_growth": 0.0, "sheet": "sprites/egg.png", "frame_w": 32, "frame_h": 32 },
    { "id": "sprout", "name": "Sprout", "min_growth": 0.1, "sheet": "sprites/sprout.png", "frame_w": 32, "frame_h": 32 }
  ],
  "animations": { "walk": [0, 1, 2, 3], "sit": [4, 5] },
  "moods": { "content": "sit", "focused": "focus", "worried": "worry", "exhausted": "sleep", "celebrate": "celebrate" },
  "triggers": { "needs_you": "pop", "job_passed": "cheer", "near_limit": "worry", "idle": "nap" },
  "roam": { "edges": ["bottom", "left", "right"], "speed_px_s": 30 }
}
```

| Key | Rule |
|---|---|
| `schema_version` | `1` or `2`. A `.json` pixel sheet anywhere in the file needs `2`. |
| `frame_w`, `frame_h` | Integers 8 to 64. The base frame size. With `stages`, equals stage 0. |
| `scale` | Integer 1 to 4. Display multiplier, nearest-neighbour. |
| `fps` | Integer 1 to 24. |
| `sheet` | Path of the single sprite sheet (conventionally `sprite.png`; under version 2 it may be a `.json` pixel sheet). Required when `stages` is absent, forbidden when it is present. Without `stages`, the single sheet is stage 0. |
| `stages` | Optional, 1 to 6 entries, ordered. See below. |
| `animations` | Map of animation name to a list of frame indexes (1 to 64 integers, 0 or more). Names `^[a-z][a-z0-9_]{1,23}$`, at most 32. |
| `moods` | Required. Keys exactly `content`, `focused`, `worried`, `exhausted`, `celebrate`; values are animation names. |
| `triggers` | Required. Keys exactly `needs_you`, `job_passed`, `near_limit`, `idle`; values are animation names. |
| `roam` | Required. `edges`: non-empty, unique subset of `bottom`, `left`, `right`. `speed_px_s`: number 5 to 120. |

**Required animations:** `walk`, `sit`, `nap`, `pop`, `cheer`, `worry`, `focus`, `sleep`,
`celebrate`. Extra animations are allowed (mapped by nobody in v1, reserved for later).

**Sheets.** PNG, RGBA recommended. Frames are laid out row-major in a grid of `frame_w` by
`frame_h` cells; the sheet's width and height must be exact multiples of the cell size. Frame
index `i` is the `i`-th cell counting left to right, then top to bottom. Every sheet must have
cells for the highest frame index any animation uses.

**Pixel sheets (schema_version 2).** A sheet whose path ends in `.json` is a pixel sheet: the
frames written out as characters, which Sanduhr rasterizes at install. It is a UTF-8 JSON object
with exactly these keys:

```json
{
  "palette": ["#22d3ee", "#a855f7", "#ec4899"],
  "frame_w": 8,
  "frame_h": 8,
  "frames": [
    ["..0000..", ".011110.", "01122110", "01122110", "01111110", ".011110.", "..0..0..", ".00..00."]
  ]
}
```

| Key | Rule |
|---|---|
| `palette` | 1 to 16 `#rrggbb` colors. `#ffffff` (any case) is rejected: pure white burns on OLED panels. |
| `frame_w`, `frame_h` | Integers 8 to 32 (pixel sheets are sized for a companion), equal to the cell size of the stage (or the top-level size, for a single `sheet`) that uses the sheet. |
| `frames` | 1 to 256 frames. Each frame is exactly `frame_h` strings, top row first, and each string is exactly `frame_w` characters, left pixel first. |

Each character is one pixel: `.` is transparent, and `0`-`9`, `a`-`f` (lowercase) are an index into
`palette`, which must be less than the palette's length. Every pixel is fully opaque or fully
transparent. Frame `i` is `frames[i]`, and the sheet must have a frame for the highest frame index
any animation uses. A pixel sheet is at most 2 MB. It is an ordinary pack file: it is listed in
`files`, counts toward the 64-file and 10 MB limits, and goes through the content and trademark
scans like every other JSON file. `sprite.json` itself is never a sheet.

**Stages.** Each entry is `{ id, name, min_growth, sheet, frame_w, frame_h }`:

- `id`: kebab-case, 2 to 20 characters, unique. `name`: 1 to 24 characters.
- `min_growth`: number in `[0, 1]`. The first stage is `0`; values are strictly increasing.
  A stage is shown when `growth >= min_growth` and the next stage's `min_growth` is not reached.
- `sheet`: PNG path (or, under version 2, a `.json` pixel sheet), listed in `files`, unique per
  stage. Stages may mix the two types.
- `frame_w`, `frame_h`: 8 to 64. Stages may differ in cell size (a later stage may be larger).

`animations` is shared: **every stage must provide every required animation**, because every stage
sheet is indexed by the same animation table. Stages are anchored bottom-centre when drawn.

**Mapping.** `moods` maps the companion's mood to an animation. `triggers` maps one-shot events
to an animation that plays once, then the mood animation resumes.

| Mapping | Key | Meaning |
|---|---|---|
| mood | `content` | Under pace. |
| mood | `focused` | Near pace. |
| mood | `worried` | Weekly use at 85% or more, or over pace. |
| mood | `exhausted` | At the limit. Sleeps until the reset. |
| mood | `celebrate` | The weekly reset just happened. |
| trigger | `needs_you` | A session is waiting for the user. |
| trigger | `job_passed` | A watched job finished green. |
| trigger | `near_limit` | A usage threshold was crossed. |
| trigger | `idle` | Nothing has happened for a while. |

**Art constraints** (checked by review, not by the validator, except where noted): original art,
no pure white (`#ffffff`; the validator enforces this for pixel-sheet palettes), transparency for
everything that is not the character, readable at the smallest scale.

### 5.6 `preview.png`

Any kind may ship one. Same PNG limits. It is shown in the install list. Keep it to the pack's
own art.

## 6. Companion behaviour (implemented by Sanduhr)

These are Sanduhr's rules, not a pack's. A pack supplies art and the mapping above; it cannot
change any of this.

- **Growth** is a number from 0 to 1 that Sanduhr computes from **coding days and active coding
  time, never from tokens or usage spent**. The pet never rewards burning the weekly limit: a
  user who stays well under pace grows exactly as fast as one who hits the cap.
- **Stage** is the stage with the highest `min_growth` that growth has reached. Growth does not go
  backwards.
- **Mood** comes from pacing: under pace is `content`, near pace is `focused`, weekly use at 85%
  or more or over pace is `worried`, at the limit is `exhausted` (the companion sleeps and wakes at
  the reset), and the reset itself plays `celebrate`.
- **The pet never dies.** There is no hunger, no decay, no loss state. Time away pauses growth.
- Triggers play once on the event, then the current mood animation resumes.

## 7. The catalog

Releases of this repository publish three kinds of asset:

- one zip per pack, `<id>-<version>.zip`
- `catalog.json`
- `catalog.json.sig`, and during a key rotation `catalog.json.sig2`

**Zip contents** are the pack folder's files at the zip root (`pack.json`, `LICENSE`, the listed
assets and the preview). Entries are sorted by path, carry a fixed 1980-01-01 timestamp and
permission bits, are stored without compression, and there are no directory entries. The zip for a
given pack version is byte-identical on every build, on every platform.

**catalog.json**

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-21T18:00:00Z",
  "packs": [
    {
      "id": "hourglass",
      "name": "Hourglass",
      "kind": "sprite",
      "version": "1.0.0",
      "sanduhr_min": "3.8.0",
      "url": "https://github.com/626Labs-LLC/sanduhr-widgets/releases/download/v1.0.0/hourglass-1.0.0.zip",
      "sha256": "<64 hex characters>",
      "size": 12345
    }
  ]
}
```

`packs` is sorted by `id`. The file is UTF-8, LF line endings, two-space indent, keys sorted, one
trailing newline. Every release re-publishes every pack, so each `url` resolves under the same tag
as the catalog that lists it.

**catalog.json.sig** is an **ECDSA P-256 (prime256v1, secp256r1) signature with SHA-256** over the
exact bytes of `catalog.json`:

- The signature is the 64-byte IEEE P1363 form: `r` then `s`, each a 32-byte big-endian unsigned
  integer, zero-padded on the left. This is .NET's
  `DSASignatureFormat.IeeeP1363FixedFieldConcatenation` and WebCrypto's ECDSA format.
- The file is those 64 bytes in base64 (standard alphabet, with padding, no line breaks), followed
  by one LF. Strip trailing whitespace before decoding; anything that does not decode to exactly
  64 bytes is an invalid signature.
- The public key is distributed and pinned as a DER **SubjectPublicKeyInfo** (91 bytes for P-256,
  base64 `MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...`). In .NET:
  `ECDsa.Create().ImportSubjectPublicKeyInfo(spki, out _)` then
  `VerifyData(catalogBytes, sig, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)`.

Why P-256 and not Ed25519: Sanduhr runs on .NET 10, whose `System.Security.Cryptography` has no
Ed25519. P-256 with P1363 signatures is what 626 Labs' other signed manifests already use (RoRoRo's
`RobloxCompatSignature`, the Mod Launcher's `ManifestSignature`), so the client verifies with the
platform's own crypto and no third-party library. Nothing had been signed or released when the
format moved, so no client ever trusted an Ed25519 key.

OpenSSL writes and reads ECDSA signatures as DER (`SEQUENCE { INTEGER r, INTEGER s }`), not P1363.
`tools/ecdsa_sig.py` (Python 3 standard library) converts between the two, strictly. Verify with
OpenSSL 3:

```
openssl base64 -d -A -in catalog.json.sig -out catalog.sig.bin          # 64 bytes, r||s
python3 tools/ecdsa_sig.py p1363-to-der catalog.sig.bin catalog.sig.der  # DER for OpenSSL
openssl dgst -sha256 -verify sanduhr-widgets-pub.pem -signature catalog.sig.der catalog.json
```

`sanduhr-widgets-pub.pem` is the same key as the pinned SPKI in PEM form
(`openssl pkey -pubin -inform DER -in spki.der -out sanduhr-widgets-pub.pem`). ECDSA signatures
are randomized, so signing the same catalog twice gives two different, equally valid signatures;
compare by verifying, never by bytes.

**Client rules.** Sanduhr, and any other client, must do these in order and stop at the first
failure:

1. Fetch `catalog.json` and `catalog.json.sig` from the latest release. Verify the signature
   against the **embedded** public key(s) before parsing anything. A catalog with no valid
   signature is discarded.
2. Reject a catalog whose `generated_at` is older than the newest one already seen (rollback).
3. For the chosen pack, check `sanduhr_min`, download `url`, and check `size` and `sha256`
   against the catalog entry before opening the zip.
4. Extract safely: only regular files, no path outside the target folder, no entry beyond the
   limits in section 3.
5. **Re-validate the pack locally** with the rules in this document, exactly as `tools/validate.py`
   does. Trust nothing the catalog or the zip claims about itself.
6. Install atomically (staging folder, then rename).

### Key rotation

The signing key is an ECDSA P-256 key. Its public half is embedded in Sanduhr as a
SubjectPublicKeyInfo. To rotate from key A to key B without stranding anyone:

1. Generate key B (the same commands as key A, below). Ship a Sanduhr release that embeds **both**
   SPKIs and accepts a valid signature from either key, on either signature file.
2. Once that release is out, set `SIGNING_KEY_NEXT` (key B) next to `SIGNING_KEY` (key A) in the
   repository secrets. The release workflow then publishes `catalog.json.sig` (key A, which old
   clients read) and `catalog.json.sig2` (key B). The catalog is signed by both for the overlap.
3. When old clients are out of support, make B the primary: `SIGNING_KEY` becomes key B, drop
   `SIGNING_KEY_NEXT`, and stop signing with A. A later Sanduhr release removes A from its
   embedded set.
4. If a key is compromised, skip the overlap: ship a Sanduhr release that drops it and rotate
   immediately. Catalogs signed only with a dropped key stop verifying, which is the point.

The private key never lives in the repository, in CI logs, or on a shared machine. Generate it
offline with OpenSSL 3 (the README has the full maintainer steps):

```
openssl ecparam -name prime256v1 -genkey -noout -out sanduhr-widgets-signing.pem
openssl ec -in sanduhr-widgets-signing.pem -pubout -outform DER | base64     # the SPKI to pin
```

`tools/sign_catalog.sh` refuses any key that is not a P-256 private key, signs SHA-256, converts
the signature to P1363, verifies it against the key's public half, and only then writes the file.
It prints the SPKI it signed with, so a release log shows which pinned key a catalog needs.
