import logging
import re
import requests
import feedparser
from datetime import datetime, timezone
from dateutil import parser as dateparser
from .models import Job

log = logging.getLogger(__name__)
TIMEOUT = 25
HEADERS = {"User-Agent": "jobhunter/1.0 (personal job search bot)"}


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    for a, b in [("&#x27;", "'"), ("&quot;", '"'), ("&amp;", "&"),
                 ("&gt;", ">"), ("&lt;", "<"), ("&#x2F;", "/")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _parse_date(s):
    if not s:
        return None
    try:
        return dateparser.parse(s).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def fetch_hn_whoishiring() -> list[Job]:
    """Hacker News 'Ask HN: Who is hiring?' — latest monthly thread."""
    # Find the most recent story
    r = requests.get(
        "https://hn.algolia.com/api/v1/search_by_date",
        params={"query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": 5},
        headers=HEADERS, timeout=TIMEOUT,
    )
    hits = r.json().get("hits", [])
    if not hits:
        return []
    story_id = hits[0].get("objectID")
    if not story_id:
        return []

    # Fetch the story + its comments
    r = requests.get(
        f"https://hn.algolia.com/api/v1/items/{story_id}",
        headers=HEADERS, timeout=TIMEOUT,
    )
    item = r.json()

    jobs = []
    for child in item.get("children", []) or []:
        text = child.get("text") or ""
        if not text or len(text) < 40:
            continue
        clean = _strip_html(text)
        # First ~120 chars usually contain "Company | Role | Location | Remote"
        headline = clean[:160]
        jobs.append(Job(
            source="hn_whoishiring",
            external_id=str(child.get("id", "")),
            title=headline[:120],
            company="",
            url=f"https://news.ycombinator.com/item?id={child.get('id')}",
            location="",
            description=clean[:5000],
            tags=[],
        ))
    log.info("hn_whoishiring: parsed %d comments", len(jobs))
    return jobs


def fetch_himalayas() -> list[Job]:
    """Himalayas.app public jobs feed."""
    r = requests.get(
        "https://himalayas.app/jobs/api?limit=100",
        headers=HEADERS, timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    jobs = []
    for j in data.get("jobs", []) or []:
        jobs.append(Job(
            source="himalayas",
            external_id=str(j.get("guid") or j.get("id") or j.get("slug", "")),
            title=j.get("title", ""),
            company=j.get("companyName", "") or j.get("company", ""),
            url=j.get("applicationLink") or j.get("url") or j.get("guid", ""),
            location=j.get("locationRestrictions") and
                     ", ".join(j.get("locationRestrictions") or []) or
                     j.get("location", "") or "",
            description=j.get("description", "") or j.get("excerpt", ""),
            posted_at=_parse_date(
                j.get("pubDate") or j.get("publishedDate") or j.get("createdAt")
            ),
            tags=(j.get("categories") or []) + (j.get("tags") or []),
        ))
    log.info("himalayas: %d jobs", len(jobs))
    return jobs


def fetch_nodesk() -> list[Job]:
    """NoDesk remote job RSS."""
    feed = feedparser.parse("https://nodesk.co/remote-jobs/index.xml")
    jobs = []
    for entry in feed.entries:
        jobs.append(Job(
            source="nodesk",
            external_id=entry.get("id") or entry.get("link", ""),
            title=entry.get("title", ""),
            company=entry.get("author", "") or "",
            url=entry.get("link", ""),
            location="remote",
            description=_strip_html(entry.get("summary", "")),
            posted_at=_parse_date(entry.get("published")),
            tags=[t.get("term", "") for t in entry.get("tags", [])],
        ))
    log.info("nodesk: %d jobs", len(jobs))
    return jobs
