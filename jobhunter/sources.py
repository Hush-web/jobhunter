import logging
from datetime import datetime, timezone
from typing import Callable
import requests
import feedparser
from dateutil import parser as dateparser
from .models import Job
from . import sources_extra

log = logging.getLogger(__name__)
TIMEOUT = 20
HEADERS = {"User-Agent": "jobhunter/1.0 (personal job search bot)"}


def _parse_date(s):
    if not s:
        return None
    try:
        return dateparser.parse(s).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def fetch_remotive() -> list[Job]:
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"
    data = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
    jobs = []
    for j in data.get("jobs", []):
        jobs.append(Job(
            source="remotive",
            external_id=str(j["id"]),
            title=j.get("title", ""),
            company=j.get("company_name", ""),
            url=j.get("url", ""),
            location=j.get("candidate_required_location", "") or "",
            description=j.get("description", ""),
            posted_at=_parse_date(j.get("publication_date")),
            tags=j.get("tags", []) or [],
            salary=j.get("salary") or None,
        ))
    return jobs


def fetch_remoteok() -> list[Job]:
    url = "https://remoteok.com/api"
    data = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
    jobs = []
    for j in data:
        if not isinstance(j, dict) or "id" not in j:
            continue
        jobs.append(Job(
            source="remoteok",
            external_id=str(j["id"]),
            title=j.get("position", ""),
            company=j.get("company", ""),
            url=j.get("url") or j.get("apply_url", ""),
            location=j.get("location", "") or "",
            description=j.get("description", ""),
            posted_at=_parse_date(j.get("date")),
            tags=j.get("tags", []) or [],
        ))
    return jobs


def fetch_arbeitnow() -> list[Job]:
    url = "https://www.arbeitnow.com/api/job-board-api"
    data = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
    jobs = []
    for j in data.get("data", []):
        if not j.get("remote"):
            continue
        jobs.append(Job(
            source="arbeitnow",
            external_id=j.get("slug", ""),
            title=j.get("title", ""),
            company=j.get("company_name", ""),
            url=j.get("url", ""),
            location=j.get("location", "") or "",
            description=j.get("description", ""),
            posted_at=_parse_date(str(j.get("created_at", ""))),
            tags=j.get("tags", []) or [],
        ))
    return jobs


def fetch_jobicy() -> list[Job]:
    url = "https://jobicy.com/api/v2/remote-jobs?count=50&geo=anywhere"
    data = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
    jobs = []
    for j in data.get("jobs", []):
        jobs.append(Job(
            source="jobicy",
            external_id=str(j.get("id", "")),
            title=j.get("jobTitle", ""),
            company=j.get("companyName", ""),
            url=j.get("url", ""),
            location=j.get("jobGeo", "") or "",
            description=j.get("jobDescription", "") or j.get("jobExcerpt", ""),
            posted_at=_parse_date(j.get("pubDate")),
            tags=[j.get("jobIndustry", "")] if j.get("jobIndustry") else [],
        ))
    return jobs


def fetch_wwr() -> list[Job]:
    url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    feed = feedparser.parse(url)
    jobs = []
    for entry in feed.entries:
        jobs.append(Job(
            source="wwr",
            external_id=entry.get("id") or entry.get("link", ""),
            title=entry.get("title", ""),
            company=entry.get("author", "") or "",
            url=entry.get("link", ""),
            location="remote",
            description=entry.get("summary", ""),
            posted_at=_parse_date(entry.get("published")),
            tags=[t.get("term", "") for t in entry.get("tags", [])],
        ))
    return jobs


# ---- Registry ----

SOURCES: dict[str, Callable[[], list[Job]]] = {
    "remotive": fetch_remotive,
    "remoteok": fetch_remoteok,
    "arbeitnow": fetch_arbeitnow,
    "jobicy": fetch_jobicy,
    "wwr": fetch_wwr,
    "hn_whoishiring": sources_extra.fetch_hn_whoishiring,
    "himalayas": sources_extra.fetch_himalayas,
    "nodesk": sources_extra.fetch_nodesk,
}

SOURCE_NAMES = list(SOURCES.keys())


# ---- Public API ----

def fetch_one(name: str) -> list[Job]:
    """Fetch jobs from a single named source."""
    if name not in SOURCES:
        raise ValueError(f"Unknown source: {name}. Try one of: {SOURCE_NAMES}")
    return SOURCES[name]()


def fetch_all(sources: list[str] | None = None) -> list[Job]:
    """
    Fetch jobs from all (or selected) sources.
    If `sources` is None, uses every registered source.
    """
    selected = sources or SOURCE_NAMES
    all_jobs: list[Job] = []

    for name in selected:
        fn = SOURCES.get(name)
        if fn is None:
            log.warning("Unknown source: %s", name)
            continue
        try:
            jobs = fn()
            log.info("%s: %d jobs", name, len(jobs))
            all_jobs.extend(jobs)
        except Exception as e:
            log.warning("%s failed: %s", name, e)

    return all_jobs