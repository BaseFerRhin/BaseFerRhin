"""Protocol for pluggable source file extractors."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from src.domain.models.raw_record import RawRecord


@runtime_checkable
class SourceExtractor(Protocol):
    """Extracts archaeological source files into normalized raw records."""

    def extract(self, source_path: Path) -> list[RawRecord]:
        """Read ``source_path`` and return one or more ``RawRecord`` rows."""
        ...

    def supported_formats(self) -> list[str]:
        """File extensions this extractor handles (lowercase, with dot)."""
        ...
