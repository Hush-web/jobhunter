import logging
import argparse
import yaml
from pathlib import Path
from .db import DB
from .sources import fetch_all
from .scoring import score_job
from .notify import format_digest, send_digest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("jobhunter")


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--db", default="jobs.db")
    ap.add_argument("--min-score", type=int, default=None,
                    help="override config min_score (use 0 to see everything)")
    ap.add_argument("--notify", action="store_true",
                    help="send Telegram digest")
    ap.add_argument("--show-reasons", action="store_true",
                    help="print score breakdown for each job")
    args = ap.parse_args()

    config = load_config(args.config)
    min_score = args.min_score if args.min_score is not None else config.get("min_score", 4)

    db = DB(args.db)
    jobs = fetch_all()
    log.info("Fetched %d jobs total", len(jobs))

    new_count = 0
    skipped = 0
    for job in jobs:
        if db.exists(job.uid, job.url):
            skipped += 1
            continue
        score, reasons = score_job(job, config)
        db.insert(job, score, reasons)
        new_count += 1

    log.info("Inserted %d new jobs (%d duplicates skipped)", new_count, skipped)

    rows = db.top(min_score=min_score, limit=50)
    print(format_digest(rows))

    if args.show_reasons:
        print("\n--- Score breakdown ---")
        for r in rows:
            print(f"[{r['score']}] {r['title'][:70]}")
            print(f"     {r['score_reasons']}")

    if args.notify:
        send_digest(rows)


if __name__ == "__main__":
    main()
