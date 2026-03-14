"""APScheduler-based job runner for recurring pipeline execution."""

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from clawbot.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def _make_scheduler(config) -> BlockingScheduler:
    """Build an APScheduler instance backed by SQLite for job persistence."""
    jobstores = {
        "default": SQLAlchemyJobStore(url=f"sqlite:///{config.state_db_path}")
    }
    return BlockingScheduler(
        jobstores=jobstores,
        timezone=config.timezone,
    )


def run_scheduler(config) -> None:
    """Start the Clawbot scheduler.

    Registers two jobs:
    - scrape_and_connect: runs the full pipeline on the configured interval.
    - poll_and_message: polls for acceptances and sends messages.

    Pressing Ctrl+C gracefully shuts down the scheduler.
    """
    orchestrator = Orchestrator(config)
    scheduler = _make_scheduler(config)

    def full_pipeline_job():
        logger.info("Scheduled job: full_pipeline_job starting.")
        try:
            orchestrator.run_pipeline()
        except Exception as exc:
            logger.exception("Pipeline job failed: %s", exc)

    # Register jobs (replace_existing=True so restarts don't duplicate)
    scheduler.add_job(
        full_pipeline_job,
        trigger="interval",
        hours=config.scrape_interval_hours,
        id="full_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow up to 1hr late start
    )

    def handle_shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping scheduler.")
        scheduler.shutdown(wait=False)
        orchestrator.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info(
        "Scheduler started. Pipeline runs every %dh. Press Ctrl+C to stop.",
        config.scrape_interval_hours,
    )
    scheduler.start()
