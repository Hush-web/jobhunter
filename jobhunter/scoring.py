from datetime import datetime
from .models import Job


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("-", " ").replace("/", " ").split())


def score_job(job: Job, config: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    title = _norm(job.title)
    body = _norm(f"{job.description} {' '.join(job.tags)}")
    full = f"{title} {body}"

    # Hard reject: seniority words in title
    for kw in config.get("title_blocklist", []):
        if _norm(kw) in title:
            return -99, [f"BLOCKED seniority '{kw}'"]

    # Hard reject: off-domain roles in title
    for kw in config.get("title_role_blocklist", []):
        if _norm(kw) in title:
            return -99, [f"BLOCKED role '{kw}'"]

    # Title gate: must contain at least one target term
    target_title_terms = config.get("title_must_match_any", [])
    if target_title_terms:
        if not any(_norm(t) in title for t in target_title_terms):
            return 0, ["title has no target keyword"]

    # Positive matches (title + body)
    for kw, weight in config.get("positive_keywords", {}).items():
        if _norm(kw) in full:
            score += weight
            reasons.append(f"+{weight} {kw}")

    # Negative matches (title + body)
    for kw, weight in config.get("negative_keywords", {}).items():
        if _norm(kw) in full:
            score -= weight
            reasons.append(f"-{weight} {kw}")

    # Title bonus (extra weight for target terms in title)
    for kw, weight in config.get("title_bonus", {}).items():
        if _norm(kw) in title:
            score += weight
            reasons.append(f"+{weight} title '{kw}'")

    # Location rules
    loc = _norm(job.location)
    for blocked in config.get("blocked_locations", []):
        if _norm(blocked) in loc:
            score -= 10
            reasons.append(f"-10 blocked loc '{blocked}'")
            break
    for ok in config.get("ok_locations", []):
        if _norm(ok) in loc:
            score += 2
            reasons.append(f"+2 ok loc '{ok}'")
            break

    # Freshness
    if job.posted_at:
        days = (datetime.utcnow() - job.posted_at).days
        if days <= 3:
            score += 2
            reasons.append("+2 fresh")
        elif days > 14:
            score -= 2
            reasons.append("-2 stale")

    return score, reasons
