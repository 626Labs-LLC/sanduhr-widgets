# Security

## Reporting a malicious or unsafe pack

If you find a pack in the catalog that does something it should not (carries active content,
tries to escape its folder, impersonates a brand, or smuggles in something the format forbids),
report it privately first.

- Use **GitHub private vulnerability reporting** on this repository: Security tab, then
  "Report a vulnerability". Include the pack id, version, and what you saw.
- Do not open a public issue for a live problem. A public issue tells everyone before the pack is
  pulled.

What happens next: the pack is yanked first (removed from the catalog and a new signed release
published without it), then investigated, then the validator is fixed so the same trick fails CI.
Clients re-validate every pack locally, so a hole in the validator and a hole in a client are
tracked separately.

## Reporting a flaw in the format, the validator, or the signing model

Same channel. Examples: a path that passes `tools/validate.py` but escapes on extraction, a PNG or
font that passes the checks but should not, a way to get a catalog accepted without a valid
signature.

## Scope

In scope: `docs/FORMAT.md`, `tools/`, `schema/`, `.github/workflows/`, the packs under `packs/`,
and the signed release assets.

Out of scope: the Sanduhr application itself. Report those through Sanduhr's own repository.

## The signing key

The ECDSA P-256 private key lives offline with the maintainer and in the repository secret
`SIGNING_KEY`. If you believe it was exposed, say so through the channel above. The response is a
key rotation as described in `docs/FORMAT.md`.
