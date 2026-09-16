import json
import sqlite3
from datetime import datetime
from .models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    uid TEXT PRIMARY KEY,
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
"""


class DB:
    def __init__(self, path: str = "jobs.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def exists(self, uid: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM jobs WHERE uid = ?", (uid,))
        return cur.fetchone() is not None

    def insert(self, job: Job, score: int, reasons: list[str]) -> None:
        self.conn.execute("""
            INSERT INTO jobs (uid, source, external_id, title, company, url,
                             location, description, posted_at, tags, salary,
                             score, score_reasons, seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.uid, job.source, job.external_id, job.title, job.company,
            job.url, job.location, job.description[:4000],
            job.posted_at.isoformat() if job.posted_at else None,
            json.dumps(job.tags), job.salary, score, json.dumps(reasons),
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