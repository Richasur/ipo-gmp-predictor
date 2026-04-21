"""
scheduler.py — Optional local scheduler using APScheduler
Use this when you want to run the pipeline locally instead of GitHub Actions.
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline.run_pipeline import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

@scheduler.scheduled_job("interval", minutes=30)
def scheduled_run():
    logging.info("⏰ Scheduled pipeline run starting...")
    try:
        run()
    except Exception as e:
        logging.error(f"Pipeline error: {e}")


if __name__ == "__main__":
    logging.info("Starting local scheduler (every 30 min)...")
    scheduler.start()
