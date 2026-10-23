#!/usr/bin/env python3
"""Convert ECDSA P-256 signatures between DER (what OpenSSL writes) and IEEE P1363 (what the
catalog publishes and .NET verifies with DSASignatureFormat.IeeeP1363FixedFieldConcatenation).

Python 3, standard library only. No key material passes through this file: it only reshapes
signatures, which are public.

    python tools/ecdsa_sig.py der-to-p1363 sig.der sig.bin   # SEQUENCE{r, s} -> r||s (64 bytes)
    python tools/ecdsa_sig.py p1363-to-der sig.bin sig.der   # r||s (64 bytes) -> SEQUENCE{r, s}

A DER ECDSA signature is `30 len 02 len(r) r 02 len(s) s`, each INTEGER minimal and positive
(a leading 00 when the high bit is set). P1363 is r and s as 32-byte big-endian numbers, back to
back. Parsing is strict: anything else is an error, never a best guess.
"""
import sys

FIELD = 32  # bytes per coordinate on P-256
# P-256 group order; r and s must lie in [1, N-1]
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def _read_len(data, pos):
    if pos >= len(data):
        raise ValueError("truncated DER length")
    first = data[pos]
    if first < 0x80:
        return first, pos + 1
    if first != 0x81:  # a P-256 signature is at most 72 bytes, so only the short form or 0x81 fits
        raise ValueError("unsupported DER length form")
    if pos + 1 >= len(data) or data[pos + 1] < 0x80:
        raise ValueError("non-minimal DER length")
    return data[pos + 1], pos + 2


def _read_int(data, pos):
    if pos >= len(data) or data[pos] != 0x02:
        raise ValueError("expected a DER INTEGER")
    length, pos = _read_len(data, pos + 1)
    body = data[pos:pos + length]
    if length == 0 or len(body) != length:
        raise ValueError("truncated DER INTEGER")
    if body[0] & 0x80:
        raise ValueError("negative DER INTEGER")
    if length > 1 and body[0] == 0 and not body[1] & 0x80:
        raise ValueError("non-minimal DER INTEGER")
    return int.from_bytes(body, "big"), pos + length


def der_to_p1363(der):
    """SEQUENCE { INTEGER r, INTEGER s } -> 64 bytes r||s."""
    der = bytes(der)
    if not der or der[0] != 0x30:
        raise ValueError("not a DER SEQUENCE")
    length, pos = _read_len(der, 1)
    if pos + length != len(der):
        raise ValueError("DER SEQUENCE length does not match the data")
    r, pos = _read_int(der, pos)
    s, pos = _read_int(der, pos)
    if pos != len(der):
        raise ValueError("trailing data inside the DER SEQUENCE")
    for name, v in (("r", r), ("s", s)):
        if not 1 <= v < N:
            raise ValueError("%s is out of range for P-256" % name)
    return r.to_bytes(FIELD, "big") + s.to_bytes(FIELD, "big")


def _der_int(v):
    body = v.to_bytes((v.bit_length() + 7) // 8 or 1, "big")
    if body[0] & 0x80:
        body = b"\x00" + body
    return b"\x02" + bytes([len(body)]) + body


def p1363_to_der(sig):
    """64 bytes r||s -> SEQUENCE { INTEGER r, INTEGER s }."""
    sig = bytes(sig)
    if len(sig) != 2 * FIELD:
        raise ValueError("a P-256 P1363 signature is exactly 64 bytes, got %d" % len(sig))
    r = int.from_bytes(sig[:FIELD], "big")
    s = int.from_bytes(sig[FIELD:], "big")
    for name, v in (("r", r), ("s", s)):
        if not 1 <= v < N:
            raise ValueError("%s is out of range for P-256" % name)
    body = _der_int(r) + _der_int(s)
    return b"\x30" + bytes([len(body)]) + body  # at most 70 bytes, so the short length form


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ops = {"der-to-p1363": der_to_p1363, "p1363-to-der": p1363_to_der}
    if len(argv) != 3 or argv[0] not in ops:
        sys.stderr.write("usage: ecdsa_sig.py {der-to-p1363|p1363-to-der} <in> <out>\n")
        return 2
    try:
        with open(argv[1], "rb") as f:
            out = ops[argv[0]](f.read())
    except (OSError, ValueError) as e:
        sys.stderr.write("ecdsa_sig: %s\n" % e)
        return 1
    with open(argv[2], "wb") as f:
        f.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
