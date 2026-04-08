"""OLE2 .doc text extraction via antiword subprocess."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class AntiwordNotFoundError(RuntimeError):
    pass


class DocExtractor:
    """Extract raw text from .doc OLE2 files using antiword."""

    def __init__(self) -> None:
        if not shutil.which("antiword"):
            raise AntiwordNotFoundError(
                "antiword is required for .doc OLE2 files. "
                "Install with: brew install antiword"
            )

    def supported_formats(self) -> list[str]:
        return [".doc"]

    def extract_text(self, doc_path: Path) -> str:
        """Extract full text from a .doc file via antiword."""
        result = subprocess.run(
            ["antiword", str(doc_path)],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.error("antiword failed for %s: %s", doc_path.name, stderr)
            raise RuntimeError(f"antiword failed: {stderr}")

        text = result.stdout.decode("utf-8", errors="replace")
        logger.info("DOC %s: %d characters extracted", doc_path.name, len(text))
        return text
