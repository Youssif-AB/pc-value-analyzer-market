from __future__ import annotations

import base64
from datetime import datetime

import httpx

from backend.app.config import Settings
from backend.app.services.normalization import normalize_condition
from ml.market_sources.base import MarketSourceError, SourceListing


class EbayBrowseSource:
    name = "ebay"
    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    search_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=25.0, follow_redirects=True)

    def _token(self) -> str:
        if not self.settings.ebay_client_id or not self.settings.ebay_client_secret:
            raise MarketSourceError("eBay source is not configured")
        raw = f"{self.settings.ebay_client_id}:{self.settings.ebay_client_secret}".encode()
        response = self.client.post(
            self.token_url,
            headers={
                "Authorization": f"Basic {base64.b64encode(raw).decode()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        if response.status_code >= 400:
            raise MarketSourceError(f"eBay OAuth failed ({response.status_code})")
        token = response.json().get("access_token")
        if not token:
            raise MarketSourceError("eBay OAuth returned no access_token")
        return str(token)

    def fetch(self) -> list[SourceListing]:
        token = self._token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.settings.ebay_marketplace_id,
            "Accept-Language": "en-CA" if self.settings.ebay_marketplace_id == "EBAY_CA" else "en-US",
        }
        by_id: dict[str, SourceListing] = {}
        per_query = max(1, min(self.settings.ebay_result_limit, 200))
        for query in self.settings.ebay_queries:
            response = self.client.get(
                self.search_url,
                headers=headers,
                params={
                    "q": query,
                    "category_ids": self.settings.ebay_category_id,
                    "limit": per_query,
                    "sort": "newlyListed",
                    "fieldgroups": "EXTENDED",
                    "filter": "price:[150..15000],priceCurrency:CAD,buyingOptions:{FIXED_PRICE|BEST_OFFER}",
                },
            )
            if response.status_code >= 400:
                raise MarketSourceError(f"eBay Browse search failed ({response.status_code})")
            for item in response.json().get("itemSummaries", []):
                price = item.get("price") or {}
                try:
                    value = float(price.get("value"))
                except (TypeError, ValueError):
                    continue
                currency = str(price.get("currency") or "CAD").upper()
                source_id = str(item.get("itemId") or "")
                title = str(item.get("title") or "").strip()
                if not source_id or not title or value <= 0:
                    continue
                listed_at = None
                raw_date = item.get("itemCreationDate") or item.get("itemOriginDate")
                if raw_date:
                    try:
                        listed_at = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                    except ValueError:
                        listed_at = None
                image = item.get("image") or {}
                by_id[source_id] = SourceListing(
                    source=self.name,
                    source_listing_id=source_id,
                    title=title,
                    summary=item.get("shortDescription"),
                    price=value,
                    currency=currency,
                    condition=normalize_condition(item.get("condition")),
                    listing_type="active_asking",
                    url=item.get("itemWebUrl"),
                    image_url=image.get("imageUrl"),
                    listed_at=listed_at,
                )
        return list(by_id.values())
