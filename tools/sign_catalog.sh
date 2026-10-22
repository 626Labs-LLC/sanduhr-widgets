#!/usr/bin/env bash
# Sign dist/catalog.json with Ed25519 and write dist/catalog.json.sig (base64, one line).
#
# Needs OpenSSL 3.x (for `pkeyutl -rawin`). The private key is read from, in order:
#   SIGNING_KEY_FILE   path to a PEM file (local use)
#   SIGNING_KEY        the PEM text itself (CI secret)
# Optional second key for a rotation overlap (see docs/FORMAT.md, Key rotation):
#   SIGNING_KEY_NEXT_FILE / SIGNING_KEY_NEXT   -> also writes catalog.json.sig2
#
# Usage:  SIGNING_KEY_FILE=~/keys/sanduhr-widgets-signing.pem tools/sign_catalog.sh [catalog.json]
#
# The signature covers the exact bytes of the catalog, so do not edit, re-encode or re-indent
# catalog.json after signing. The script verifies each signature with the matching public key
# before it finishes, and never prints key material.
set -euo pipefail

CATALOG="${1:-dist/catalog.json}"
if [[ ! -f "$CATALOG" ]]; then
  echo "sign_catalog: $CATALOG not found. Run tools/build_catalog.py first." >&2
  exit 1
fi
if ! openssl version | grep -Eq 'OpenSSL 3|LibreSSL (3\.[7-9]|[4-9])'; then
  echo "sign_catalog: OpenSSL 3.x is required (pkeyutl -rawin). Found: $(openssl version)" >&2
  exit 1
fi

umask 077
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# resolve_key <FILE_VAR> <TEXT_VAR> <dest> -> 0 when a key was staged at <dest>
resolve_key() {
  local file_var="$1" text_var="$2" dest="$3"
  if [[ -n "${!file_var:-}" ]]; then
    [[ -f "${!file_var}" ]] || { echo "sign_catalog: $file_var does not point at a file" >&2; exit 1; }
    cp "${!file_var}" "$dest"
  elif [[ -n "${!text_var:-}" ]]; then
    printf '%s\n' "${!text_var}" > "$dest"
  else
    return 1
  fi
}

sign_with() {
  local key="$1" out="$2"
  if ! openssl pkey -in "$key" -noout -text 2>/dev/null | head -n 1 | grep -qi 'ED25519'; then
    echo "sign_catalog: the signing key is not an Ed25519 private key" >&2
    exit 1
  fi
  openssl pkeyutl -sign -rawin -inkey "$key" -in "$CATALOG" -out "$WORK/sig.bin"
  openssl pkey -in "$key" -pubout -out "$WORK/pub.pem"
  openssl pkeyutl -verify -rawin -pubin -inkey "$WORK/pub.pem" -in "$CATALOG" -sigfile "$WORK/sig.bin" >/dev/null
  openssl base64 -A -in "$WORK/sig.bin" -out "$out"
  printf '\n' >> "$out"
  local fp
  fp="$(openssl pkey -in "$key" -pubout -outform DER | openssl dgst -sha256 | awk '{print $NF}')"
  echo "sign_catalog: wrote $out (public key sha256 $fp)"
}

if ! resolve_key SIGNING_KEY_FILE SIGNING_KEY "$WORK/key.pem"; then
  echo "sign_catalog: no signing key. Set SIGNING_KEY_FILE (path) or SIGNING_KEY (PEM text)." >&2
  exit 1
fi
sign_with "$WORK/key.pem" "${CATALOG}.sig"

if resolve_key SIGNING_KEY_NEXT_FILE SIGNING_KEY_NEXT "$WORK/key-next.pem"; then
  sign_with "$WORK/key-next.pem" "${CATALOG}.sig2"
fi
