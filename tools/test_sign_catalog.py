#!/usr/bin/env python3
"""Tests for tools/sign_catalog.sh and tools/ecdsa_sig.py. Standard library only.

    python tools/test_sign_catalog.py

Every key here is a throwaway P-256 key that OpenSSL generates in a temporary folder for one
test and that is deleted with the folder. The signatures are checked twice, independently: by
OpenSSL (after converting P1363 back to DER) and by a small pure-Python P-256 verifier that reads
the 64-byte r||s exactly the way .NET's IeeeP1363FixedFieldConcatenation does.

Needs `openssl` (3.x) and `bash` on PATH. Outside CI the signing tests skip when either is
missing; in CI (the CI environment variable is set) they fail instead, so a runner without
OpenSSL can never turn the suite green by skipping.
"""
import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ecdsa_sig  # noqa: E402

SCRIPT = HERE / "sign_catalog.sh"
OPENSSL = shutil.which("openssl")
BASH = os.environ.get("BASH_FOR_TESTS") or shutil.which("bash")
IN_CI = bool(os.environ.get("CI"))

# DER prefix of every P-256 SubjectPublicKeyInfo: SEQUENCE { SEQUENCE { id-ecPublicKey,
# prime256v1 }, BIT STRING (0 unused bits) }, followed by the 65-byte uncompressed point 04||X||Y.
P256_SPKI_PREFIX = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200")

# ---- a tiny P-256 verifier (FIPS 186-4 / SEC 1), for an independent check -------------------
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = P - 3
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
N = ecdsa_sig.N
G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
     0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


def _add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    (x1, y1), (x2, y2) = p1, p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1 + A) * pow(2 * y1, -1, P) % P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    return x3, (lam * (x1 - x3) - y1) % P


def _mul(k, pt):
    out = None
    while k:
        if k & 1:
            out = _add(out, pt)
        pt = _add(pt, pt)
        k >>= 1
    return out


def spki_point(spki):
    if len(spki) != 91 or not spki.startswith(P256_SPKI_PREFIX) or spki[26] != 0x04:
        raise ValueError("not an uncompressed P-256 SubjectPublicKeyInfo")
    x = int.from_bytes(spki[27:59], "big")
    y = int.from_bytes(spki[59:91], "big")
    if (y * y - (x * x * x + A * x + B)) % P:
        raise ValueError("point is not on P-256")
    return x, y


def verify_p1363(spki, message, sig):
    """True when `sig` (64 bytes r||s) is a valid ECDSA P-256 / SHA-256 signature of `message`."""
    if len(sig) != 64:
        return False
    r, s = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
    if not (1 <= r < N and 1 <= s < N):
        return False
    q = spki_point(spki)
    e = int.from_bytes(hashlib.sha256(message).digest(), "big")
    w = pow(s, -1, N)
    pt = _add(_mul(e * w % N, G), _mul(r * w % N, q))
    return pt is not None and pt[0] % N == r


# ---- helpers -------------------------------------------------------------------------------
def need_tools(case):
    missing = [n for n, p in (("openssl", OPENSSL), ("bash", BASH)) if not p]
    if missing:
        msg = "%s not on PATH" % " and ".join(missing)
        if IN_CI:
            case.fail(msg + " (required in CI)")
        case.skipTest(msg)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, **kw)


class Keyed(unittest.TestCase):
    def setUp(self):
        need_tools(self)
        self.tmp = Path(tempfile.mkdtemp(prefix="sanduhr-widgets-sign-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.catalog = self.tmp / "catalog.json"
        self.catalog.write_bytes(
            b'{\n  "generated_at": "2026-01-01T00:00:00Z",\n  "packs": [],\n  "schema_version": 1\n}\n')

    def new_key(self, name, curve="prime256v1"):
        path = self.tmp / name
        r = run([OPENSSL, "ecparam", "-name", curve, "-genkey", "-noout", "-out", str(path)])
        self.assertEqual(r.returncode, 0, r.stderr)
        return path

    def spki(self, key):
        r = run([OPENSSL, "pkey", "-in", str(key), "-pubout", "-outform", "DER"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def sign(self, **env):
        e = {k: v for k, v in os.environ.items()
             if k not in ("SIGNING_KEY", "SIGNING_KEY_FILE", "SIGNING_KEY_NEXT", "SIGNING_KEY_NEXT_FILE")}
        e["PYTHON"] = sys.executable
        e.update({k: str(v) for k, v in env.items()})
        return run([BASH, SCRIPT.as_posix(), self.catalog.as_posix()], env=e, text=True)

    def read_sig(self, suffix=".sig"):
        raw = (self.tmp / ("catalog.json" + suffix)).read_bytes()
        self.assertTrue(raw.endswith(b"\n") and raw.count(b"\n") == 1, "one line, LF")
        self.assertNotIn(b"\r", raw)
        sig = base64.b64decode(raw.strip(), validate=True)
        self.assertEqual(len(sig), 64)
        return sig

    def openssl_verifies(self, key, message_path, sig):
        pub = self.tmp / "pub.pem"
        run([OPENSSL, "pkey", "-in", str(key), "-pubout", "-out", str(pub)])
        der = self.tmp / "check.der"
        der.write_bytes(ecdsa_sig.p1363_to_der(sig))
        r = run([OPENSSL, "dgst", "-sha256", "-verify", str(pub), "-signature", str(der), str(message_path)])
        return r.returncode == 0


class SignCatalog(Keyed):
    def test_signs_and_verifies_with_python_and_openssl(self):
        key = self.new_key("k.pem")
        r = self.sign(SIGNING_KEY_FILE=key.as_posix())
        self.assertEqual(r.returncode, 0, r.stderr)
        sig = self.read_sig()
        spki = self.spki(key)
        self.assertEqual(len(spki), 91)
        self.assertTrue(verify_p1363(spki, self.catalog.read_bytes(), sig))
        self.assertTrue(self.openssl_verifies(key, self.catalog, sig))
        self.assertIn(base64.b64encode(spki).decode(), r.stdout, "prints the SPKI to pin")
        self.assertNotIn("PRIVATE", r.stdout + r.stderr)
        self.assertFalse((self.tmp / "catalog.json.sig2").exists())

    def test_key_from_pem_text_and_rotation_overlap(self):
        a, b = self.new_key("a.pem"), self.new_key("b.pem")
        r = self.sign(SIGNING_KEY=a.read_text(), SIGNING_KEY_NEXT_FILE=b.as_posix())
        self.assertEqual(r.returncode, 0, r.stderr)
        msg = self.catalog.read_bytes()
        sig1, sig2 = self.read_sig(".sig"), self.read_sig(".sig2")
        self.assertTrue(verify_p1363(self.spki(a), msg, sig1))
        self.assertTrue(verify_p1363(self.spki(b), msg, sig2))
        self.assertFalse(verify_p1363(self.spki(b), msg, sig1), "each file is signed by its own key")

    def test_tampered_catalog_byte_fails(self):
        key = self.new_key("k.pem")
        self.assertEqual(self.sign(SIGNING_KEY_FILE=key.as_posix()).returncode, 0)
        sig = self.read_sig()
        tampered = bytearray(self.catalog.read_bytes())
        tampered[tampered.index(b"2026")] ^= 0x01  # 2026 -> 3026
        bad = self.tmp / "tampered.json"
        bad.write_bytes(bytes(tampered))
        self.assertFalse(verify_p1363(self.spki(key), bytes(tampered), sig))
        self.assertFalse(self.openssl_verifies(key, bad, sig))

    def test_tampered_signature_byte_fails(self):
        key = self.new_key("k.pem")
        self.assertEqual(self.sign(SIGNING_KEY_FILE=key.as_posix()).returncode, 0)
        sig = bytearray(self.read_sig())
        sig[40] ^= 0x80
        self.assertFalse(verify_p1363(self.spki(key), self.catalog.read_bytes(), bytes(sig)))

    def test_other_key_does_not_verify(self):
        key, other = self.new_key("k.pem"), self.new_key("other.pem")
        self.assertEqual(self.sign(SIGNING_KEY_FILE=key.as_posix()).returncode, 0)
        self.assertFalse(verify_p1363(self.spki(other), self.catalog.read_bytes(), self.read_sig()))

    def test_rejects_a_key_on_another_curve(self):
        key = self.new_key("p384.pem", curve="secp384r1")
        r = self.sign(SIGNING_KEY_FILE=key.as_posix())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not an ECDSA P-256", r.stderr)
        self.assertFalse((self.tmp / "catalog.json.sig").exists())

    def test_rejects_an_ed25519_key(self):
        key = self.tmp / "ed.pem"
        if run([OPENSSL, "genpkey", "-algorithm", "ed25519", "-out", str(key)]).returncode:
            self.skipTest("this OpenSSL cannot make Ed25519 keys")
        r = self.sign(SIGNING_KEY_FILE=key.as_posix())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not an ECDSA P-256", r.stderr)

    def test_no_key_is_an_error(self):
        r = self.sign()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no signing key", r.stderr)


class DerP1363(unittest.TestCase):
    def test_round_trip_including_short_and_high_bit_values(self):
        for r, s in ((1, 2), (N - 1, N - 2), (0x80 << 248, 0x7F), (0xFF << 240, 1 << 255)):
            p1363 = r.to_bytes(32, "big") + s.to_bytes(32, "big")
            der = ecdsa_sig.p1363_to_der(p1363)
            self.assertEqual(ecdsa_sig.der_to_p1363(der), p1363)

    def test_high_bit_gets_a_leading_zero(self):
        der = ecdsa_sig.p1363_to_der((1 << 255).to_bytes(32, "big") + (1).to_bytes(32, "big"))
        self.assertEqual(der[2:5], b"\x02\x21\x00")

    def test_strict_parsing(self):
        good = ecdsa_sig.p1363_to_der(bytes(31) + b"\x05" + bytes(31) + b"\x07")
        bad = (
            b"",
            b"\x31" + good[1:],                    # not a SEQUENCE
            good + b"\x00",                       # trailing data
            b"\x30\x06\x02\x01\x00\x02\x01\x07",  # r = 0
            b"\x30\x07\x02\x02\x00\x05\x02\x01\x07",  # non-minimal INTEGER
            b"\x30\x06\x02\x01\x85\x02\x01\x07",  # negative INTEGER
        )
        for blob in bad:
            with self.subTest(blob=blob.hex()):
                with self.assertRaises(ValueError):
                    ecdsa_sig.der_to_p1363(blob)

    def test_p1363_must_be_64_bytes_and_in_range(self):
        for blob in (bytes(63), bytes(65), bytes(64), b"\xff" * 64):
            with self.subTest(n=len(blob)):
                with self.assertRaises(ValueError):
                    ecdsa_sig.p1363_to_der(blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
