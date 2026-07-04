from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SourceListing:
    source: str
    source_listing_id: str
    title: str
    price: float
    currency: str
    condition: str
    listing_type: str = "active"
    summary: str | None = None
    url: str | None = None
    image_url: str | None = None
    listed_at: datetime | None = None


class MarketSource(Protocol):
    name: str

    def fetch(self) -> list[SourceListing]: ...


class MarketSourceError(RuntimeError):
    pass
