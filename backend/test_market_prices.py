import json
from io import BytesIO
from urllib.request import Request

import pytest

import market_prices
from market_prices import MarketPriceError, fetch_twelve_data_prices


def test_fetch_twelve_data_prices_returns_valid_batch_prices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request: Request | None = None

    def fake_urlopen(request: Request, timeout: int) -> BytesIO:
        nonlocal captured_request
        captured_request = request
        assert timeout == 10
        return BytesIO(
            json.dumps(
                {
                    "NVDA": {"price": "182.50"},
                    "NOW": {"price": "0", "status": "error"},
                }
            ).encode()
        )

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)

    result = fetch_twelve_data_prices(["now", "NVDA", "NVDA"], "fake-key")

    assert result.prices == {"NVDA": market_prices.Decimal("182.50")}
    assert result.unavailable == ["NOW"]
    assert captured_request is not None
    assert captured_request.get_header("Authorization") == "apikey fake-key"
    assert "fake-key" not in captured_request.full_url


def test_fetch_twelve_data_prices_rejects_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: int) -> BytesIO:
        return BytesIO(
            json.dumps(
                {"status": "error", "code": 429, "message": "Limit reached"}
            ).encode()
        )

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)

    with pytest.raises(MarketPriceError):
        fetch_twelve_data_prices(["NVDA"], "fake-key")
