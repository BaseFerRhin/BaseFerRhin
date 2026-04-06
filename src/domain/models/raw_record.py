from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawRecord:
    raw_text: str = ""
    commune: Optional[str] = None
    type_mention: Optional[str] = None
    periode_mention: Optional[str] = None
    latitude_raw: Optional[float] = None
    longitude_raw: Optional[float] = None
    source_path: str = ""
    page_number: Optional[int] = None
    extraction_method: str = ""
    ark_id: Optional[str] = None
    context_text: Optional[str] = None
    extra: dict = field(default_factory=dict)
