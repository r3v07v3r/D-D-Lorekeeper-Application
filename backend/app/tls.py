"""Self-signed TLS for the backend.

Why self-signed rather than a CA-issued certificate: this app has no fixed
domain name (it's addressed by whatever LAN/public IP the GM happens to
have), and CAs like Let's Encrypt won't issue certificates for bare IP
addresses. Instead, the backend generates its own certificate once and
keeps it (see ensure_certificate), and clients trust it via **certificate
pinning** rather than the normal CA trust chain: the exact SHA-256
fingerprint of this certificate is embedded in the GM's share code (see
frontend/src/api/shareCode.ts) and/or auto-registered locally for the GM's
own machine (see electron/main.js). A client only accepts this server if
the live certificate's fingerprint matches the one it was told to expect -
conceptually the same trust model as SSH host key checking. This still
gets you real encryption (protects the campaign passphrase and session
tokens in transit over the internet) plus real authentication of *this
specific server* - just not anonymous "any CA-issued cert is fine" trust,
which isn't available without a domain anyway.

The certificate is deliberately long-lived (10 years) and self-contained:
regenerating it would change its fingerprint and break every previously
shared/pinned code, so once generated for an install it should be left
alone.
"""
import datetime
import logging
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)


def ensure_certificate(config_dir: Path) -> tuple[Path, Path]:
    """Returns (cert_path, key_path), generating a self-signed cert/key pair
    under config_dir if one doesn't already exist there.
    """
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    cert_path = config_dir / "cert.pem"
    key_path = config_dir / "key.pem"

    if cert_path.exists() and key_path.exists():
        return cert_path, key_path

    logger.info("Generating a new self-signed TLS certificate at %s", cert_path)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "lorekeeper-backend")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


def get_fingerprint(cert_path: Path) -> str:
    """Returns the certificate's SHA-256 fingerprint as colon-separated
    uppercase hex (e.g. "AA:BB:CC:...") - matches the format Node's
    `crypto.X509Certificate.fingerprint256` and
    `tls.TLSSocket.getPeerCertificate().fingerprint256` produce, which is
    what the Electron side compares against (see electron/main.js). This
    was cross-checked directly against Node during development, not assumed.
    """
    cert = x509.load_pem_x509_certificate(Path(cert_path).read_bytes())
    digest = cert.fingerprint(hashes.SHA256())
    return ":".join(f"{b:02X}" for b in digest)
