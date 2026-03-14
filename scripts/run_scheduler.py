#!/usr/bin/env python3
"""Start the Clawbot scheduler for recurring pipeline runs."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clawbot.utils.config_loader import load_config
from clawbot.scheduler.job_runner import run_scheduler


def main():
    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    run_scheduler(config)


if __name__ == "__main__":
    main()
