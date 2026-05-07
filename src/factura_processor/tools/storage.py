"""Save invoice PDFs to disk, grouped by issuer."""

import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r"[^a-z0-9._-]+")


def _slugify(name: str) -> str:
    """Turn an arbitrary issuer name into a filesystem-safe folder name.

    Strips accents, lowercases, and collapses anything that isn't a safe
    character into a single underscore.
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _UNSAFE_CHARS.sub("_", ascii_only.lower()).strip("_")
    return slug or "unknown"


def save_invoice_pdf(
    pdf_bytes: bytes,
    filename: str,
    emisor: str,
    base_dir: str | Path,
) -> Path:
    """Write a PDF under ``<base_dir>/<emisor>/<filename>``.

    The issuer name is slugified so it works as a directory on every OS. If a
    file with the same name already exists we append a numeric suffix instead
    of overwriting — different invoices sometimes share an attachment name.
    """
    issuer_dir = Path(base_dir) / _slugify(emisor)
    issuer_dir.mkdir(parents=True, exist_ok=True)

    target = issuer_dir / filename
    if target.exists():
        stem, suffix = target.stem, target.suffix
        counter = 1
        while True:
            candidate = issuer_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                target = candidate
                break
            counter += 1

    target.write_bytes(pdf_bytes)
    logger.info("Saved invoice PDF to %s", target)
    return target
