import json
from io import BytesIO
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from investments import market_prices
from investments.market_prices import (
    MarketPriceError,
    eodhd_symbol_for,
    fetch_eodhd_prices,
)


def test_eodhd_symbol_for_uses_us_exchange_and_verified_eur_override() -> None:
    assert eodhd_symbol_for("nvda", "usd") == "NVDA.US"
    assert eodhd_symbol_for("ail", "eur") == "AI.PA"
    assert eodhd_symbol_for("unknown", "eur") is None


def test_fetch_eodhd_prices_returns_latest_valid_prices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_requests: list[Request] = []

    def fake_urlopen(request: Request, timeout: int) -> BytesIO:
        captured_requests.append(request)
        assert timeout == 10

        if "/AI.PA?" in request.full_url:
            return BytesIO(
                json.dumps([{"date": "2026-08-27", "close": 166.78}]).encode()
            )

        return BytesIO(json.dumps([{"date": "2026-08-26", "close": 209.66}]).encode())

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)

    result = fetch_eodhd_prices(
        {"NVDA": "NVDA.US", "AIL": "AI.PA"},
        "fake-key",
    )

    assert result.prices == {
        "AIL": market_prices.Decimal("166.78"),
        "NVDA": market_prices.Decimal("209.66"),
    }
    assert result.unavailable == []
    assert len(captured_requests) == 2

    for request in captured_requests:
        query = parse_qs(urlparse(request.full_url).query)
        assert query["api_token"] == ["fake-key"]
        assert query["fmt"] == ["json"]
        assert query["order"] == ["d"]


def test_fetch_eodhd_prices_marks_empty_results_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: int) -> BytesIO:
        return BytesIO(b"[]")

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)

    result = fetch_eodhd_prices({"UNKNOWN": "UNKNOWN.US"}, "fake-key")

    assert result.prices == {}
    assert result.unavailable == ["UNKNOWN"]


def test_fetch_eodhd_prices_rejects_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: int) -> BytesIO:
        return BytesIO(json.dumps({"code": 429, "message": "Limit reached"}).encode())

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)

    with pytest.raises(MarketPriceError):
        fetch_eodhd_prices({"NVDA": "NVDA.US"}, "fake-key")
