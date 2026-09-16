from datetime import datetime
from .models import Job


def score_job(job: Job, config: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    text = f"{job.title} {job.description} {' '.join(job.tags)}".lower()

    for kw, weight in config.get("positive_keywords", {}).items():
        if kw.lower() in text:
            score += weight
            reasons.append(f"+{weight} '{kw}'")

    for kw, weight in config.get("negative_keywords", {}).items():
        if kw.lower() in text:
            score -= weight
            reasons.append(f"-{weight} '{kw}'")

    loc = (job.location or "").lower()
    for blocked in config.get("blocked_locations", []):
        if blocked.lower() in loc:
            score -= 10
            reasons.append(f"-10 blocked location '{blocked}'")
            break

    for ok in config.get("ok_locations", []):
        if ok.lower() in loc:
            score += 2
            reasons.append(f"+2 ok location '{ok}'")
            break

    if job.posted_at:
        days = (datetime.utcnow() - job.posted_at).days
        if days <= 3:
            score += 2
            reasons.append("+2 posted <=3d")
        elif days > 14:
            score -= 2
            reasons.append("-2 stale (>14d)")

    return score, reasons