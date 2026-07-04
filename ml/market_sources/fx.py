from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.config import Settings
from ml.market_sources.base import MarketSourceError


@dataclass
class FxConverter:
    settings: Settings
    client: httpx.Client | None = None

    def usd_to_cad(self) -> float:
        if self.settings.usd_to_cad_override:
            return float(self.settings.usd_to_cad_override)
        if not self.settings.bank_of_canada_fx_enabled:
            raise MarketSourceError("USD/CAD conversion is required but Bank of Canada FX is disabled")
        client = self.client or httpx.Client(timeout=15.0, follow_redirects=True)
        response = client.get(
            "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json",
            params={"recent": 1},
        )
        if response.status_code >= 400:
            raise MarketSourceError(f"Bank of Canada FX request failed ({response.status_code})")
        observations = response.json().get("observations", [])
        if not observations:
            raise MarketSourceError("Bank of Canada FX response contained no observations")
        value = (observations[-1].get("FXUSDCAD") or {}).get("v")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise MarketSourceError("Bank of Canada FX response contained no numeric FXUSDCAD value") from exc

    def to_cad(self, value: float, currency: str) -> float:
        code = currency.upper()
        if code == "CAD":
            return float(value)
        if code == "USD":
            return float(value) * self.usd_to_cad()
        raise MarketSourceError(f"Unsupported source currency: {currency}")
