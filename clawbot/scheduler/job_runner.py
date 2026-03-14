"""APScheduler-based job runner for recurring pipeline execution."""

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from clawbot.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Module-level orchestrator so APScheduler can reference the job function
_orchestrator = None


def _run_pipeline_job():
    """Top-level job function (must be module-level for APScheduler serialization)."""
    logger.info("Scheduled job: pipeline starting.")
    try:
        _orchestrator.run_pipeline()
    except Exception as exc:
        logger.exception("Pipeline job failed: %s", exc)


def run_scheduler(config) -> None:
    """Start the Clawbot scheduler. Press Ctrl+C to stop."""
    global _orchestrator
    _orchestrator = Orchestrator(config)

    # Use in-memory job store — pipeline state is persisted in SQLite separately
    scheduler = BlockingScheduler(timezone=config.timezone)

    scheduler.add_job(
        _run_pipeline_job,
        trigger="interval",
        hours=config.scrape_interval_hours,
        id="full_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
        next_run_time=__import__("datetime").datetime.now(),  # Run immediately on start
    )

    def handle_shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping scheduler.")
        scheduler.shutdown(wait=False)
        _orchestrator.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info(
        "Scheduler started. Pipeline runs every %dh. Press Ctrl+C to stop.",
        config.scrape_interval_hours,
    )
    scheduler.start()
