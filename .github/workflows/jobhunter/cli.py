import logging
import argparse
import yaml
from pathlib import Path
from .db import DB
from .sources import fetch_all
from .scoring import score_job
from .notify import format_digest, send_telegram

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("jobhunter")


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--db", default="jobs.db")
    ap.add_argument("--min-score", type=int, default=None)
    ap.add_argument("--notify", action="store_true", help="send Telegram digest")
    args = ap.parse_args()

    config = load_config(args.config)
    min_score = args.min_score if args.min_score is not None else config.get("min_score", 7)

    db = DB(args.db)
    jobs = fetch_all()
    log.info("Fetched %d jobs total", len(jobs))

    new_count = 0
    for job in jobs:
        if db.exists(job.uid):
            continue
        score, reasons = score_job(job, config)
        db.insert(job, score, reasons)
        new_count += 1

    log.info("Inserted %d new jobs", new_count)

    rows = db.top(min_score=min_score, limit=50)
    digest = format_digest(rows)
    print(digest)

    if args.notify:
        send_telegram(digest)


if __name__ == "__main__":
    main()