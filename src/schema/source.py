from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class SourceMetadata:
    source_id: str
    title: str
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    url: Optional[str] = None
    source_type: str = "web_article"
    reliability_score: float = 0.5
    tags: List[str] = field(default_factory=list)
