"""Eight-step ETL pipeline with checkpoints and review queue."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console

from src.application.config import PipelineConfig
from src.domain.filters.chrono_filter import filter_records
from src.application.pipeline_support import (
    apply_extract,
    apply_geocode,
    apply_validate,
    checksum,
    pack_state,
    site_id,
    source_for_record,
    unpack_state,
)
from src.application.review_queue import ReviewQueue
from src.domain.deduplication.deduplicator import SiteDeduplicator
from src.domain.models.raw_record import RawRecord
from src.domain.normalizers import SiteNormalizer
from src.infrastructure.extractors.factory import ExtractorFactory, UnsupportedFormatError
from src.infrastructure.extractors.gallica_extractor import GallicaExtractor
from src.infrastructure.extractors.gallica_metadata_extractor import GallicaMetadataExtractor
from src.infrastructure.persistence import CSVExporter, ExportStats, GeoJSONExporter, SQLiteRepository

logger = logging.getLogger(__name__)

STEPS = (
    "DISCOVER",
    "INGEST",
    "EXTRACT",
    "NORMALIZE",
    "DEDUPLICATE",
    "GEOCODE",
    "VALIDATE",
    "EXPORT",
)


class Pipeline:
    def __init__(self) -> None:
        self._console = Console()
        self._review = ReviewQueue()

    def run(self, config: PipelineConfig, start_from: str | None = None) -> dict[str, Any]:
        proc = config.data_dir / "processed"
        proc.mkdir(parents=True, exist_ok=True)
        log_path = proc / "pipeline_log.json"
        start_idx = STEPS.index(start_from) if start_from else 0
        state: dict[str, Any] = {"raw_records": [], "sites": []}
        try:
            state = self._run_steps(proc, log_path, start_idx, start_from, state, config)
        finally:
            self._review.save(proc / "review_queue.json")
        return state

    def _run_steps(
        self,
        proc: Path,
        log_path: Path,
        start_idx: int,
        start_from: str | None,
        state: dict[str, Any],
        config: PipelineConfig,
    ) -> dict[str, Any]:
        for i, step in enumerate(STEPS):
            if i < start_idx:
                p = proc / f"{step}.json"
                if not p.is_file():
                    raise FileNotFoundError(f"Missing checkpoint {p}; cannot start_from {start_from}")
                state = unpack_state(json.loads(p.read_text(encoding="utf-8"))["state"])
                continue
            inp, t0 = checksum(state), datetime.now(timezone.utc).isoformat()
            cached = self._load_cached(proc, step, inp)
            self._console.print(f"[bold cyan]{step}[/bold cyan] start")
            logger.info("step %s start raw=%d sites=%d", step, len(state["raw_records"]), len(state["sites"]))
            self._append_log(
                log_path,
                {"step": step, "event": "start", "ts": t0, "input_md5": inp, "input_raw": len(state["raw_records"]), "input_sites": len(state["sites"])},
            )
            if cached is not None:
                state = cached
                self._console.print(f"[bold cyan]{step}[/bold cyan] [dim]skipped (idempotent)[/dim]")
            else:
                try:
                    state = self._dispatch(step, state, config)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("step %s failed", step)
                    self._review.add({}, step, str(exc))
                    raise
                (proc / f"{step}.json").write_text(
                    json.dumps({"input_md5": inp, "state": pack_state(state)}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            self._append_log(
                log_path,
                {"step": step, "event": "end", "ts": datetime.now(timezone.utc).isoformat(), "output_raw": len(state["raw_records"]), "output_sites": len(state["sites"])},
            )
            self._console.print(f"[bold cyan]{step}[/bold cyan] done raw={len(state['raw_records'])} sites={len(state['sites'])}")
            logger.info("step %s end raw=%d sites=%d", step, len(state["raw_records"]), len(state["sites"]))
        return state

    def _append_log(self, path: Path, rec: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def _load_cached(self, proc: Path, step: str, inp: str) -> dict[str, Any] | None:
        p = proc / f"{step}.json"
        if not p.is_file():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return unpack_state(data["state"]) if data.get("input_md5") == inp else None

    def _dispatch(self, step: str, state: dict[str, Any], config: PipelineConfig) -> dict[str, Any]:
        if step == "DISCOVER":
            return self._discover(state, config)
        if step == "INGEST":
            return self._ingest(state, config)
        if step == "EXTRACT":
            return apply_extract(state, self._review)
        if step == "NORMALIZE":
            return self._normalize(state, config)
        if step == "DEDUPLICATE":
            return self._deduplicate(state, config)
        if step == "GEOCODE":
            return apply_geocode(state, config, self._review)
        if step == "VALIDATE":
            return apply_validate(state, self._review)
        return self._export(state, config)

    def _discover(self, state: dict[str, Any], config: PipelineConfig) -> dict[str, Any]:
        ex = GallicaExtractor()

        async def _run() -> list[RawRecord]:
            acc: list[RawRecord] = []
            for q in config.gallica_queries:
                try:
                    acc.extend(await ex.extract(q, config.ocr_quality_threshold))
                except Exception as e:  # noqa: BLE001
                    self._review.add({"query": q}, "DISCOVER", str(e))
            return acc

        return {**state, "raw_records": list(state["raw_records"]) + asyncio.run(_run())}

    def _ingest(self, state: dict[str, Any], config: PipelineConfig) -> dict[str, Any]:
        rows: list[RawRecord] = list(state["raw_records"])
        factory = ExtractorFactory()

        try:
            meta_ex = GallicaMetadataExtractor()
            rows.extend(meta_ex.extract(config.gallica_metadata_path))
        except Exception as e:  # noqa: BLE001
            self._review.add({"path": str(config.gallica_metadata_path)}, "INGEST", str(e))

        for src in config.sources:
            path = Path(src["path"])
            stype = str(src.get("type", "")).lower() or None
            opts = dict(src.get("options", {}))
            try:
                extractor = factory.get_extractor(path, source_type=stype, **opts)
                extracted = extractor.extract(path)
                rows.extend(extracted)
                logger.info("INGEST %s (%s): %d records", path.name, stype or path.suffix, len(extracted))
            except UnsupportedFormatError:
                self._review.add(dict(src), "INGEST", f"unsupported type {stype!r}")
            except Exception as e:  # noqa: BLE001
                logger.warning("INGEST %s failed: %s", path.name, e)
                self._review.add(dict(src), "INGEST", str(e))

        fc = config.filter
        depts = set(fc.departments) if fc.departments else None
        pays_set = set(fc.pays) if fc.pays else None
        rows = filter_records(rows, chrono=fc.chrono, departments=depts, pays=pays_set)

        return {**state, "raw_records": rows}

    def _normalize(self, state: dict[str, Any], config: PipelineConfig) -> dict[str, Any]:
        norm, sites = SiteNormalizer(), []
        for rec in state["raw_records"]:
            try:
                sid = site_id(rec)
                sites.append(norm.normalize(rec, sid, source_for_record(rec, sid)))
            except Exception as e:  # noqa: BLE001
                self._review.add(asdict(rec), "NORMALIZE", str(e))
        return {"raw_records": state["raw_records"], "sites": sites}

    def _deduplicate(self, state: dict[str, Any], config: PipelineConfig) -> dict[str, Any]:
        d = SiteDeduplicator(
            merge_threshold=config.dedup_merge_threshold,
            review_threshold=config.dedup_review_threshold,
        )
        merged, pairs = d.deduplicate(state["sites"])
        for p in pairs:
            self._review.add(p, "DEDUPLICATE", "similarity_review")
        return {**state, "sites": merged}

    def _export(self, state: dict[str, Any], config: PipelineConfig) -> dict[str, Any]:
        sites, o = state["sites"], config.output_dir
        SQLiteRepository().save(sites, o / "sites.sqlite")
        GeoJSONExporter().export(sites, o / "sites.geojson")
        CSVExporter().export(sites, o / "sites.csv")
        es = ExportStats()
        es.display(es.compute(sites))
        return state
