"""CLI: ``python -m src --config config.yaml``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from src.application.config import PipelineConfig
from src.application.pipeline import STEPS, Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="BaseFerRhin ETL pipeline")
    parser.add_argument("--config", type=Path, required=True, help="Path to YAML pipeline config")
    parser.add_argument(
        "--start-from",
        choices=list(STEPS),
        default=None,
        help="Resume from this step (requires prior checkpoints under data/processed/)",
    )
    args = parser.parse_args()
    with args.config.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = PipelineConfig.model_validate(raw)
    logging.basicConfig(level=getattr(logging, cfg.log_level.upper(), logging.INFO))
    log = logging.getLogger(__name__)
    try:
        Pipeline().run(cfg, start_from=args.start_from)
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
