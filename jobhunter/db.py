import json
import re
import sqlite3
from datetime import datetime
from .models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    uid TEXT PRIMARY KEY,
    norm_url TEXT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    location TEXT,
    description TEXT,
    posted_at TEXT,
    tags TEXT,
    salary TEXT,
    score INTEGER DEFAULT 0,
    score_reasons TEXT,
    seen_at TEXT NOT NULL,
    status TEXT DEFAULT 'new'
);
CREATE INDEX IF NOT EXISTS idx_score ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_seen ON jobs(seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_norm_url ON jobs(norm_url);
"""


def normalize_url(url: str) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.rstrip("/")
    # strip trailing numeric suffix from WWR/RemoteOK style slugs like "-1", "-2"
    u = re.sub(r"-\d+$", "", u)
    return u


class DB:
    def __init__(self, path: str = "jobs.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        # Add norm_url if the table predates this column
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(jobs)")}
        if "norm_url" not in cols:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN norm_url TEXT")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_norm_url ON jobs(norm_url)")

    def exists(self, uid: str, url: str = "") -> bool:
        cur = self.conn.execute("SELECT 1 FROM jobs WHERE uid = ?", (uid,))
        if cur.fetchone() is not None:
            return True
        if url:
            norm = normalize_url(url)
            if norm:
                cur = self.conn.execute(
                    "SELECT 1 FROM jobs WHERE norm_url = ?", (norm,)
                )
                if cur.fetchone() is not None:
                    return True
        return False

    def insert(self, job: Job, score: int, reasons: list[str]) -> None:
        self.conn.execute("""
            INSERT INTO jobs (uid, norm_url, source, external_id, title, company,
                             url, location, description, posted_at, tags, salary,
                             score, score_reasons, seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.uid,
            normalize_url(job.url),
            job.source,
            job.external_id,
            job.title,
            job.company,
            job.url,
            job.location,
            job.description[:4000],
            job.posted_at.isoformat() if job.posted_at else None,
            json.dumps(job.tags),
            job.salary,
            score,
            json.dumps(reasons),
            datetime.utcnow().isoformat(),
        ))
        self.conn.commit()

    def top(self, min_score: int = 7, limit: int = 50) -> list[sqlite3.Row]:
        cur = self.conn.execute("""
            SELECT * FROM jobs
            WHERE score >= ? AND status = 'new'
            ORDER BY score DESC, seen_at DESC
            LIMIT ?
        """, (min_score, limit))
        return cur.fetchall()

    def mark_applied(self, uid: str) -> None:
        self.conn.execute(
            "UPDATE jobs SET status = 'applied' WHERE uid = ?", (uid,)
        )
        self.conn.commit()
