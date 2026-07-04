from __future__ import annotations

import httpx

from backend.app.config import Settings
from ml.market_sources.bestbuy import BestBuySource
from ml.market_sources.ebay import EbayBrowseSource
from ml.market_sources.fx import FxConverter


def test_ebay_source_maps_browse_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/oauth2/token'):
            return httpx.Response(200, json={'access_token': 'token'})
        assert request.headers['x-ebay-c-marketplace-id'] == 'EBAY_CA'
        return httpx.Response(200, json={'itemSummaries': [{
            'itemId': 'v1|123|0',
            'title': 'Gaming PC Ryzen 7 9800X3D RTX 5070 32GB DDR5 2TB NVMe',
            'shortDescription': 'Excellent gaming desktop',
            'price': {'value': '2499.99', 'currency': 'CAD'},
            'condition': 'Used',
            'itemWebUrl': 'https://example.test/ebay/123',
            'image': {'imageUrl': 'https://example.test/123.jpg'},
            'itemCreationDate': '2026-08-20T12:00:00.000Z',
        }]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(
        ebay_client_id='id',
        ebay_client_secret='secret',
        ebay_search_queries='gaming desktop',
        ebay_result_limit=5,
    )
    rows = EbayBrowseSource(settings, client=client).fetch()
    assert len(rows) == 1
    assert rows[0].source == 'ebay'
    assert rows[0].price == 2499.99
    assert rows[0].currency == 'CAD'
    assert rows[0].listing_type == 'active_asking'


def test_bestbuy_source_returns_new_and_open_box() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if '/v1/products' in request.url.path:
            return httpx.Response(200, json={'products': [{
                'sku': 555,
                'name': 'Gaming Desktop Ryzen 7 9700X RTX 5070 32GB DDR5 1TB SSD',
                'salePrice': 1999.99,
                'regularPrice': 2199.99,
                'url': 'https://example.test/bestbuy/555',
                'image': 'https://example.test/555.jpg',
                'shortDescription': 'Gaming desktop',
            }]})
        return httpx.Response(200, json={'results': [{
            'sku': '555',
            'names': {'title': 'Gaming Desktop Ryzen 7 9700X RTX 5070 32GB DDR5 1TB SSD'},
            'descriptions': {'short': 'Gaming desktop'},
            'links': {'web': 'https://example.test/bestbuy/555/openbox'},
            'images': {'standard': 'https://example.test/555.jpg'},
            'offers': [{'condition': 'excellent', 'prices': {'current': 1749.99, 'regular': 2199.99}}],
        }]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(bestbuy_api_key='key', bestbuy_result_limit=10)
    rows = BestBuySource(settings, client=client).fetch()
    assert {row.listing_type for row in rows} == {'retail_new', 'retail_open_box'}
    assert all(row.currency == 'USD' for row in rows)


def test_fx_converter_uses_bank_of_canada_shape() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'observations': [{'d': '2026-08-19', 'FXUSDCAD': {'v': '1.3824'}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    converter = FxConverter(Settings(), client=client)
    assert converter.to_cad(100, 'USD') == 138.24


def test_blank_fx_override_is_treated_as_unset(monkeypatch):
    from backend.app.config import Settings

    monkeypatch.setenv("USD_TO_CAD_OVERRIDE", "")
    settings = Settings(_env_file=None)
    assert settings.usd_to_cad_override is None
