"""Tests for app.tls: self-signed certificate generation and fingerprinting.

The fingerprint format (colon-separated uppercase SHA-256 hex) was
cross-checked directly against Node's crypto.X509Certificate.fingerprint256
and a live TLS handshake during development (see PR description) - these
tests cover the Python side's own consistency, not that cross-check.
"""
import re

from app.tls import ensure_certificate, get_fingerprint

FINGERPRINT_RE = re.compile(r"^([0-9A-F]{2}:){31}[0-9A-F]{2}$")


def test_generates_cert_and_key_files(tmp_path):
    cert_path, key_path = ensure_certificate(tmp_path)
    assert cert_path.exists()
    assert key_path.exists()
    assert cert_path.read_bytes().startswith(b"-----BEGIN CERTIFICATE-----")
    assert b"PRIVATE KEY" in key_path.read_bytes()


def test_is_idempotent_across_calls(tmp_path):
    cert_path_1, key_path_1 = ensure_certificate(tmp_path)
    fingerprint_1 = get_fingerprint(cert_path_1)

    cert_path_2, key_path_2 = ensure_certificate(tmp_path)
    fingerprint_2 = get_fingerprint(cert_path_2)

    assert cert_path_1 == cert_path_2
    assert key_path_1 == key_path_2
    assert fingerprint_1 == fingerprint_2  # same cert bytes, not regenerated


def test_different_config_dirs_get_different_certificates(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    cert_a, _ = ensure_certificate(dir_a)
    cert_b, _ = ensure_certificate(dir_b)

    assert get_fingerprint(cert_a) != get_fingerprint(cert_b)


def test_fingerprint_format(tmp_path):
    cert_path, _ = ensure_certificate(tmp_path)
    fingerprint = get_fingerprint(cert_path)

    assert FINGERPRINT_RE.match(fingerprint), fingerprint
