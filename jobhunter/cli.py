import logging
import argparse
import yaml
from pathlib import Path

from .db import DB
from .sources import fetch_all, SOURCE_NAMES
from .scoring import score_job
from .notify import format_digest, send_digest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("jobhunter")


# ---------- Helpers ----------

def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


# ---------- Subcommand: fetch ----------

def cmd_fetch(args):
    """Fetch new jobs from all (or one) source, score them, store in DB."""
    config = load_config(args.config)
    min_score = args.min_score if args.min_score is not None else config.get("min_score")

    db = DB(args.db)

    sources = [args.source] if args.source else None
    jobs = fetch_all(sources=sources)
    log.info("Fetched %d jobs total", len(jobs))

    new_count = 0
    for job in jobs:
        if db.exists(job.uid):
            continue
        score, reasons = score_job(job, config)
        db.insert(job, score, reasons)
        new_count += 1

    log.info("Inserted %d new jobs (skipped duplicates)", new_count)

    rows = db.top(min_score=min_score, limit=50)
    digest = format_digest(rows)
    print(digest)

    if args.show_reasons:
        print("\n--- Reasons ---")
        for row in rows:
            print(f"{row.title} @ {row.company}: {row.reasons}")

    if args.notify:
        send_telegram(digest)


# ---------- Subcommand: sources ----------

def cmd_sources(args):
    """List all available job sources."""
    print("Available sources:")
    for s in SOURCE_NAMES:
        print(f"  • {s}")


# ---------- Subcommand: digest ----------

def cmd_digest(args):
    """Print the current digest from the DB (no fetching)."""
    config = load_config(args.config)
    min_score = args.min_score if args.min_score is not None else config.get("min_score")

    db = DB(args.db)
    rows = db.top(min_score=min_score, limit=50)
    digest = format_digest(rows)
    print(digest)

    if args.notify:
        send_telegram(digest)


# ---------- Main: wire up subcommands ----------

def main():
    ap = argparse.ArgumentParser(
        prog="jobhunter",
        description="Job discovery tool that aggregates jobs from multiple sources."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # --- jobhunter fetch ---
    p_fetch = sub.add_parser("fetch", help="Fetch new jobs from all sources")
    p_fetch.add_argument("--config", default="config.yaml", help="Path to config file")
    p_fetch.add_argument("--db", default="jobs.db", help="Path to SQLite DB")
    p_fetch.add_argument(
        "--min-score",
        type=int,
        default=None,
        help="Override config min_score (use 0 to see everything)"
    )
    p_fetch.add_argument(
        "--source",
        default=None,
        help="Fetch from a single source only (e.g. remoteok)"
    )
    p_fetch.add_argument(
        "--notify",
        action="store_true",
        help="Send Telegram digest after fetching"
    )
    p_fetch.add_argument(
        "--show-reasons",
        action="store_true",
        help="Print score breakdown for each job"
    )
    p_fetch.set_defaults(func=cmd_fetch)

    # --- jobhunter sources ---
    p_sources = sub.add_parser("sources", help="List available job sources")
    p_sources.set_defaults(func=cmd_sources)

    # --- jobhunter digest ---
    p_digest = sub.add_parser("digest", help="Print current job digest from DB")
    p_digest.add_argument("--config", default="config.yaml")
    p_digest.add_argument("--db", default="jobs.db")
    p_digest.add_argument("--min-score", type=int, default=None)
    p_digest.add_argument("--notify", action="store_true")
    p_digest.set_defaults(func=cmd_digest)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
