# sanduhr-widgets

The curated catalog of widget packs for the Desk in Sanduhr für Claude (Windows). A pack changes
how the Desk looks and behaves without running a line of code: themes, color palettes, effect
presets, fonts, and animated companions.

Format v1 is **data only**. No scripts, no executables, no HTML. The catalog is signed, every pack
is hashed, and Sanduhr re-validates each one locally before it installs.

## Install

From Sanduhr 3.8 or later: **Settings > Desk > Widgets**. Pick a pack, install, done. Sanduhr
fetches the signed catalog from this repository's latest release, checks the signature, then the
hash, then validates the pack itself.

## Pack kinds

| Kind | What it ships | Files |
|---|---|---|
| `theme` | Widget themes in Sanduhr's own theme format | `themes/*.json` |
| `palette` | Named gradients of 1 to 4 color stops | `palettes.json` |
| `effects` | `glow`, `sweep`, `shimmer` and `pulse` presets | `effects.json` |
| `font` | TTF or OTF fonts, OFL-1.1 or Apache-2.0 only | `*.ttf`, `*.otf` |
| `sprite` | A Desk companion: stages, moods, animations | `sprite.json` + PNG sheets |

One kind per pack. The spec is [docs/FORMAT.md](docs/FORMAT.md); JSON shapes are in
[schema/](schema/).

## First-party packs

| Pack | Kind | What it is |
|---|---|---|
| `oled-neon` | theme | Four true-black emissive themes: Void Synthwave, Void Ember, Void Aurora, Void Toxic |
| `oled-neon-palettes` | palette | Eight gradients: synthwave, sunset, ocean, aurora, ember, bubblegum, toxic, gold |
| `oled-neon-effects` | effects | Six slow presets: breathe, heartbeat, scanline, aurora-sweep, embers, halo |
| `hourglass` | sprite | A pixel-art hourglass that grows through four stages. Sand level is growth |

The companion grows from **coding days and active coding time, never from tokens or usage spent**,
and it never dies. Details in [docs/FORMAT.md](docs/FORMAT.md), "Companion behaviour".

## Check a pack locally

Python 3 only, no pip.

```
python tools/validate.py                  # every pack, same checks CI runs
python tools/validate.py packs/hourglass  # one pack
python tools/validate.py --strict         # theme design-rule warnings fail too
python tools/test_validate.py             # the tools' own tests
python tools/test_sign_catalog.py         # signing tests (needs openssl and bash)
```

`tools/validate.py` prints one line per finding and exits non-zero on any error.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md). Short version: one pack per PR, original work, a license
from the allowed list with its text in `LICENSE`, and no third-party marks or logos (that includes
Anthropic and Claude marks and model names used as branding). A maintainer reviews every pack.

To report a malicious pack, see [SECURITY.md](SECURITY.md).

## How the signing works

- A release tag (`v*`) triggers `.github/workflows/release.yml`.
- It validates all packs, builds one reproducible zip per pack, and writes `catalog.json` (id,
  name, kind, version, `sanduhr_min`, download URL, sha256, size).
- It signs the exact bytes of `catalog.json` with an ECDSA P-256 / SHA-256 private key held in the
  repository secret `SIGNING_KEY` and uploads `catalog.json.sig` (the 64-byte P1363 signature,
  base64) next to it.
- Sanduhr embeds the matching public key as a SubjectPublicKeyInfo. It verifies the signature, then
  the zip's sha256, then re-validates the pack with the same rules as `tools/validate.py`. A failure
  at any step stops the install.

P-256 rather than Ed25519 because Sanduhr runs on .NET 10, which has no Ed25519 in
`System.Security.Cryptography`; the details are in [docs/FORMAT.md](docs/FORMAT.md) section 7.

Key rotation (two keys, overlapping releases) is in [docs/FORMAT.md](docs/FORMAT.md).

### Generating the signing key (maintainer only)

Do this once, on a machine you trust. Needs OpenSSL 3 and the GitHub CLI.

```
openssl ecparam -name prime256v1 -genkey -noout -out sanduhr-widgets-signing.pem
openssl ec -in sanduhr-widgets-signing.pem -pubout -outform DER | base64 -w0 > sanduhr-widgets-spki.b64
gh secret set SIGNING_KEY -R 626Labs-LLC/sanduhr-widgets < sanduhr-widgets-signing.pem
```

(`base64 -w0` is GNU; on macOS use `base64` alone, which already writes one line.)

Then:

1. Keep `sanduhr-widgets-signing.pem` offline (password manager or an encrypted drive). Never
   commit it; `.gitignore` blocks `*.pem` and `sanduhr-widgets-signing*` as a backstop.
2. Embed the one line in `sanduhr-widgets-spki.b64` (it starts `MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE`)
   in Sanduhr 3.8 as the catalog verification key. It is public; it is safe to commit in the app.
3. The release workflow fails with a clear error if `SIGNING_KEY` is missing, so a tag can never
   publish an unsigned catalog, and `tools/sign_catalog.sh` refuses a key that is not P-256.

To sign by hand (for example to test a build): `SIGNING_KEY_FILE=path/to/key.pem tools/sign_catalog.sh`.
The script prints the SPKI it signed with; it must equal the one Sanduhr pins.

## Layout

```
packs/            the catalog's packs, one folder each
docs/FORMAT.md    the pack format, authoritative
schema/           JSON Schema (2020-12) for pack.json, sprite.json, palettes.json, effects.json
tools/            validate.py, build_catalog.py, sign_catalog.sh, ecdsa_sig.py, tests, fixtures, art generator
.github/          CI: validate on every push and PR, release on tags
```

## License

Tooling, schemas and docs: MIT, see [LICENSE](LICENSE). Each pack carries its own license in its
folder (the first-party packs are CC-BY-4.0).

Claude is a trademark of Anthropic. This project is not affiliated with or endorsed by Anthropic.
