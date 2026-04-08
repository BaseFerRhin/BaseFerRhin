"""Pipeline configuration (YAML-backed)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class FilterConfig(BaseModel):
    chrono: bool = True
    departments: Optional[list[int]] = None
    pays: Optional[list[str]] = None


class PipelineConfig(BaseModel):
    sources: list[dict] = Field(default_factory=list)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    gallica_queries: list[str] = Field(default_factory=list)
    gallica_metadata_path: Path = Path("data/sources/gallica_metadata.json")
    ocr_quality_threshold: float = 0.4
    dedup_merge_threshold: float = 0.85
    dedup_review_threshold: float = 0.70
    geocoder_cache_path: Path = Path("data/processed/geocoder_cache.json")
    output_dir: Path = Path("data/output")
    data_dir: Path = Path("data")
    log_level: str = "INFO"
