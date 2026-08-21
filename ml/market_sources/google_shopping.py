from __future__ import annotations

import hashlib

import httpx

from backend.app.config import Settings
from backend.app.services.normalization import normalize_condition
from ml.market_sources.base import MarketSourceError, SourceListing


class GoogleShoppingSource:
    name = "google_shopping"
    search_url = "https://serpapi.com/search.json"

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or httpx.Client(
            timeout=25.0,
            follow_redirects=True,
        )

    def fetch(self) -> list[SourceListing]:
        if not self.settings.serpapi_api_key:
            raise MarketSourceError("Google Shopping source is not configured")

        by_id: dict[str, SourceListing] = {}

        for query in self.settings.google_shopping_query_list:
            response = self.client.get(
                self.search_url,
                params={
                    "engine": "google_shopping",
                    "q": query,
                    "location": self.settings.google_shopping_location,
                    "gl": self.settings.google_shopping_gl,
                    "hl": self.settings.google_shopping_hl,
                    "api_key": self.settings.serpapi_api_key,
                    "output": "json",
                },
            )

            if response.status_code >= 400:
                raise MarketSourceError(
                    f"Google Shopping / SerpApi failed ({response.status_code})"
                )

            results = response.json().get("shopping_results", [])

            for item in results[: self.settings.google_shopping_result_limit]:
                title = str(item.get("title") or "").strip()
                merchant = str(item.get("source") or "Unknown merchant").strip()

                try:
                    price = float(item.get("extracted_price"))
                except (TypeError, ValueError):
                    continue

                if not title or price <= 0:
                    continue

                product_id = str(item.get("product_id") or "").strip()

                if product_id:
                    source_id = f"{product_id}:{merchant}"
                else:
                    identity = f"{merchant}|{title}|{price}"
                    source_id = hashlib.sha256(
                        identity.encode()
                    ).hexdigest()[:32]

                condition_text = (
                    item.get("second_hand_condition")
                    or "new"
                )

                snippet = str(item.get("snippet") or "").strip()

                summary_parts = [merchant]
                if snippet:
                    summary_parts.append(snippet)

                by_id[source_id] = SourceListing(
                    source=self.name,
                    source_listing_id=source_id,
                    title=title,
                    summary=" · ".join(summary_parts),
                    price=price,
                    currency=self.settings.google_shopping_currency,
                    condition=normalize_condition(condition_text),
                    listing_type="shopping_result",
                    url=item.get("product_link"),
                    image_url=item.get("thumbnail"),
                )

        return list(by_id.values())