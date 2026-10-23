#!/usr/bin/env bash
# Sign dist/catalog.json with ECDSA P-256 / SHA-256 and write dist/catalog.json.sig: the 64-byte
# IEEE P1363 signature (r||s), base64, one line. See docs/FORMAT.md section 7.
#
# Needs OpenSSL 3.x and Python 3 (standard library; tools/ecdsa_sig.py reshapes OpenSSL's DER
# signature into P1363 and back). The private key is read from, in order:
#   SIGNING_KEY_FILE   path to a PEM file (local use)
#   SIGNING_KEY        the PEM text itself (CI secret)
# Optional second key for a rotation overlap (see docs/FORMAT.md, Key rotation):
#   SIGNING_KEY_NEXT_FILE / SIGNING_KEY_NEXT   -> also writes catalog.json.sig2
#
# Usage:  SIGNING_KEY_FILE=~/keys/sanduhr-widgets-signing.pem tools/sign_catalog.sh [catalog.json]
#
# The signature covers the exact bytes of the catalog, so do not edit, re-encode or re-indent
# catalog.json after signing. The script verifies each signature with the matching public key
# (after the round trip back to DER, so the published bytes are what gets checked) before it
# writes anything, and never prints private key material. It prints the public key's
# SubjectPublicKeyInfo (DER, base64), which is what Sanduhr pins.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CATALOG="${1:-dist/catalog.json}"
if [[ ! -f "$CATALOG" ]]; then
  echo "sign_catalog: $CATALOG not found. Run tools/build_catalog.py first." >&2
  exit 1
fi
if ! openssl version | grep -Eq '^OpenSSL 3'; then
  echo "sign_catalog: OpenSSL 3.x is required. Found: $(openssl version)" >&2
  exit 1
fi
PY="${PYTHON:-}"
if [[ -z "$PY" ]]; then
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info[0] != 3)' 2>/dev/null; then
      PY="$c"
      break
    fi
  done
fi
if [[ -z "$PY" ]]; then
  echo "sign_catalog: Python 3 is required (tools/ecdsa_sig.py). Set PYTHON to its path." >&2
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
  # A P-256 private key in either SEC1 ("EC PRIVATE KEY") or PKCS#8 PEM form.
  if ! openssl pkey -in "$key" -noout -text 2>/dev/null | grep -Eq '^(ASN1 OID: prime256v1|NIST CURVE: P-256)$'; then
    echo "sign_catalog: the signing key is not an ECDSA P-256 (prime256v1) private key" >&2
    exit 1
  fi
  openssl dgst -sha256 -sign "$key" -out "$WORK/sig.der" "$CATALOG"
  "$PY" "$HERE/ecdsa_sig.py" der-to-p1363 "$WORK/sig.der" "$WORK/sig.bin"
  local n
  n="$(wc -c < "$WORK/sig.bin" | tr -d ' ')"
  [[ "$n" == "64" ]] || { echo "sign_catalog: P1363 signature is $n bytes, expected 64" >&2; exit 1; }
  # Self-verify what will be published: P1363 back to DER, checked against the key's public half.
  openssl pkey -in "$key" -pubout -out "$WORK/pub.pem"
  "$PY" "$HERE/ecdsa_sig.py" p1363-to-der "$WORK/sig.bin" "$WORK/sig-check.der"
  if ! openssl dgst -sha256 -verify "$WORK/pub.pem" -signature "$WORK/sig-check.der" "$CATALOG" >/dev/null; then
    echo "sign_catalog: self-verification failed; nothing written" >&2
    exit 1
  fi
  openssl base64 -A -in "$WORK/sig.bin" -out "$WORK/sig.b64"
  printf '\n' >> "$WORK/sig.b64"
  cp "$WORK/sig.b64" "$out"
  local spki fp
  spki="$(openssl pkey -in "$key" -pubout -outform DER | openssl base64 -A)"
  fp="$(openssl pkey -in "$key" -pubout -outform DER | openssl dgst -sha256 | awk '{print $NF}')"
  echo "sign_catalog: wrote $out (public key SPKI sha256 $fp)"
  echo "sign_catalog: public key SPKI (DER, base64): $spki"
}

if ! resolve_key SIGNING_KEY_FILE SIGNING_KEY "$WORK/key.pem"; then
  echo "sign_catalog: no signing key. Set SIGNING_KEY_FILE (path) or SIGNING_KEY (PEM text)." >&2
  exit 1
fi
sign_with "$WORK/key.pem" "${CATALOG}.sig"

if resolve_key SIGNING_KEY_NEXT_FILE SIGNING_KEY_NEXT "$WORK/key-next.pem"; then
  sign_with "$WORK/key-next.pem" "${CATALOG}.sig2"
fi
