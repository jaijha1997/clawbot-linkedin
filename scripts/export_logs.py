#!/usr/bin/env python3
"""Export the JSONL activity log to CSV."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clawbot.utils.config_loader import load_config
from clawbot.logging.activity_logger import ActivityLogger


def main():
    config = load_config()
    logger = ActivityLogger(config.log_file, config.csv_file)
    logger.export_csv()
    print(f"Exported logs to: {config.csv_file}")


if __name__ == "__main__":
    main()
