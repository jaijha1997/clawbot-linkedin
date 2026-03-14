#!/usr/bin/env python3
"""Run one full Clawbot pipeline pass immediately (no scheduler)."""

import logging
import sys
from pathlib import Path

# Make sure the project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clawbot.utils.config_loader import load_config
from clawbot.core.orchestrator import Orchestrator


def main():
    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    orchestrator = Orchestrator(config)
    try:
        summary = orchestrator.run_pipeline()
        print("\n=== Run Summary ===")
        for key, value in summary.items():
            print(f"  {key}: {value}")
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
