from __future__ import annotations

import httpx

from backend.app.config import Settings
from backend.app.services.normalization import normalize_condition
from ml.market_sources.base import MarketSourceError, SourceListing


class BestBuySource:
    name = "bestbuy"
    products_base = "https://api.bestbuy.com/v1/products"
    open_box_base = "https://api.bestbuy.com/beta/products/openBox"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=25.0, follow_redirects=True)

    def fetch(self) -> list[SourceListing]:
        if not self.settings.bestbuy_api_key:
            raise MarketSourceError("Best Buy source is not configured")
        query = f"categoryPath.id={self.settings.bestbuy_category_id}&active=true"
        response = self.client.get(
            f"{self.products_base}({query})",
            params={
                "format": "json",
                "show": "sku,name,salePrice,regularPrice,url,image,shortDescription,manufacturer,active",
                "pageSize": max(1, min(self.settings.bestbuy_result_limit, 100)),
                "apiKey": self.settings.bestbuy_api_key,
            },
        )
        if response.status_code >= 400:
            raise MarketSourceError(f"Best Buy Products API failed ({response.status_code})")

        products = response.json().get("products", [])
        listings: list[SourceListing] = []
        skus: list[str] = []
        for product in products:
            sku = str(product.get("sku") or "")
            title = str(product.get("name") or "").strip()
            try:
                price = float(product.get("salePrice"))
            except (TypeError, ValueError):
                continue
            if not sku or not title or price <= 0:
                continue
            skus.append(sku)
            listings.append(
                SourceListing(
                    source=self.name,
                    source_listing_id=f"{sku}:new",
                    title=title,
                    summary=product.get("shortDescription"),
                    price=price,
                    currency="USD",
                    condition="new",
                    listing_type="retail_new",
                    url=product.get("url"),
                    image_url=product.get("image"),
                )
            )

        # Buying Options supports a batch of at most 100 SKUs and returns current open-box offers.
        if skus:
            batch = ",".join(skus[:100])
            open_response = self.client.get(
                f"{self.open_box_base}(sku in({batch}))",
                params={"apiKey": self.settings.bestbuy_api_key},
            )
            if open_response.status_code < 400:
                for result in open_response.json().get("results", []):
                    sku = str(result.get("sku") or "")
                    title = str((result.get("names") or {}).get("title") or "").strip()
                    summary = (result.get("descriptions") or {}).get("short")
                    links = result.get("links") or {}
                    for index, offer in enumerate(result.get("offers", [])):
                        prices = offer.get("prices") or {}
                        try:
                            price = float(prices.get("current"))
                        except (TypeError, ValueError):
                            continue
                        condition = normalize_condition(offer.get("condition"))
                        listings.append(
                            SourceListing(
                                source=self.name,
                                source_listing_id=f"{sku}:openbox:{condition}:{index}",
                                title=title,
                                summary=summary,
                                price=price,
                                currency="USD",
                                condition=condition,
                                listing_type="retail_open_box",
                                url=links.get("web"),
                                image_url=(result.get("images") or {}).get("standard"),
                            )
                        )
        return listings
