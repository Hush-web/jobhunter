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
    tags: list[str] = field(default_factory=list)
    salary: Optional[str] = None

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.external_id}"