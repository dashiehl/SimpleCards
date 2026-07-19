from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CandidateCard:
    front: str
    back: str | None = None
    kind: str = "basic"
    extra_fields: dict = field(default_factory=dict)
    source_ref: str = ""
    confidence: float = 1.0
    include: bool = True
