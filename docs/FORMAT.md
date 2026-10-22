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
| `schema_version` | `1`. |
| `frame_w`, `frame_h` | Integers 8 to 64. The base frame size. With `stages`, equals stage 0. |
| `scale` | Integer 1 to 4. Display multiplier, nearest-neighbour. |
| `fps` | Integer 1 to 24. |
| `sheet` | Path of the single sprite sheet (conventionally `sprite.png`). Required when `stages` is absent, forbidden when it is present. Without `stages`, the single sheet is stage 0. |
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

**Stages.** Each entry is `{ id, name, min_growth, sheet, frame_w, frame_h }`:

- `id`: kebab-case, 2 to 20 characters, unique. `name`: 1 to 24 characters.
- `min_growth`: number in `[0, 1]`. The first stage is `0`; values are strictly increasing.
  A stage is shown when `growth >= min_growth` and the next stage's `min_growth` is not reached.
- `sheet`: PNG path, listed in `files`, unique per stage.
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

**Art constraints** (checked by review, not by the validator): original art, no pure white
(`#ffffff`), transparency for everything that is not the character, readable at the smallest
scale.

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

**catalog.json.sig** is the base64 (standard alphabet, no line breaks) Ed25519 signature over the
exact bytes of `catalog.json`. Verify with OpenSSL 3:

```
openssl base64 -d -A -in catalog.json.sig -out catalog.sig.bin
openssl pkeyutl -verify -rawin -pubin -inkey sanduhr-widgets-pub.pem -in catalog.json -sigfile catalog.sig.bin
```

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

The signing key is Ed25519. Its public half is embedded in Sanduhr. To rotate from key A to key B
without stranding anyone:

1. Generate key B. Ship a Sanduhr release that embeds **both** public keys and accepts a valid
   signature from either, on either signature file.
2. Once that release is out, set `SIGNING_KEY_NEXT` (key B) next to `SIGNING_KEY` (key A) in the
   repository secrets. The release workflow then publishes `catalog.json.sig` (key A, which old
   clients read) and `catalog.json.sig2` (key B). The catalog is signed by both for the overlap.
3. When old clients are out of support, make B the primary: `SIGNING_KEY` becomes key B, drop
   `SIGNING_KEY_NEXT`, and stop signing with A. A later Sanduhr release removes A from its
   embedded set.
4. If a key is compromised, skip the overlap: ship a Sanduhr release that drops it and rotate
   immediately. Catalogs signed only with a dropped key stop verifying, which is the point.

The private key never lives in the repository, in CI logs, or on a shared machine. See the README
for generation.
