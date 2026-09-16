from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    posted_at: Optional[datetime] = None
    tags: list = field(default_factory=list)
    salary: Optional[str] = None

    def __post_init__(self):
        self.tags = self._normalize_tags(self.tags)

    @staticmethod
    def _normalize_tags(raw) -> list[str]:
        out: list[str] = []
        if not raw:
            return out
        for t in raw:
            if isinstance(t, str):
                if t.strip():
                    out.append(t.strip())
            elif isinstance(t, dict):
                val = t.get("term") or t.get("name") or t.get("tag") or t.get("label")
                if val:
                    out.append(str(val).strip())
            elif isinstance(t, (list, tuple, set)):
                for sub in t:
                    if isinstance(sub, str) and sub.strip():
                        out.append(sub.strip())
            else:
                s = str(t).strip()
                if s:
                    out.append(s)
        return out

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.external_id}"