import json
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from investments import market_prices
from investments.market_prices import (
    MarketPriceError,
    fetch_yahoo_prices,
    yahoo_symbol_for,
)


def test_yahoo_symbols_use_verified_listings() -> None:
    assert yahoo_symbol_for(" nvda ", "usd") == "NVDA"
    assert yahoo_symbol_for("ail", "eur") == "AI.PA"
    assert yahoo_symbol_for("sxrv", "eur") == "SXRV.DE"
    assert yahoo_symbol_for("vwce", "eur") == "VWCE.DE"
    assert yahoo_symbol_for("unknown", "eur") is None
    assert yahoo_symbol_for("../NVDA", "USD") is None


def _quote_payload(**overrides: object) -> bytes:
    meta = {
        "symbol": "SXRV.DE",
        "currency": "EUR",
        "regularMarketPrice": 1572.6,
        "regularMarketTime": 1790762400,
    } | overrides
    return json.dumps({"chart": {"error": None, "result": [{"meta": meta}]}}).encode()


def test_fetch_yahoo_prices_preserves_price_and_market_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: int) -> BytesIO:
        assert request.full_url == (
            "https://query1.finance.yahoo.com/v8/finance/chart/SXRV.DE?interval=1d&range=5d"
        )
        assert timeout == 10
        return BytesIO(_quote_payload())

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)
    result = fetch_yahoo_prices({"SXRV": "SXRV.DE"}, {"SXRV": "EUR"})
    assert result.prices["SXRV"].price == Decimal("1572.6")
    assert result.prices["SXRV"].quoted_at == datetime.fromtimestamp(1790762400, UTC)
    assert result.unavailable == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"currency": "USD"},
        {"symbol": "SXRV.L"},
        {"regularMarketPrice": 0},
        {"regularMarketPrice": -1},
        {"regularMarketPrice": "NaN"},
        {"regularMarketPrice": "Infinity"},
        {"regularMarketPrice": "10000000000000000"},
        {"regularMarketPrice": None},
        {"regularMarketTime": None},
        {"regularMarketTime": True},
        {"regularMarketTime": 0},
        {"regularMarketTime": "1790762400"},
        {"regularMarketTime": 999999999999999999999},
        {"regularMarketTime": 4102444800},
    ],
)
def test_fetch_yahoo_prices_rejects_mismatched_or_invalid_quotes(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, object],
) -> None:
    monkeypatch.setattr(
        market_prices,
        "urlopen",
        lambda *args, **kwargs: BytesIO(_quote_payload(**overrides)),
    )
    result = fetch_yahoo_prices({"SXRV": "SXRV.DE"}, {"SXRV": "EUR"})
    assert result.prices == {}
    assert result.unavailable == ["SXRV"]


@pytest.mark.parametrize(
    "payload", [b"null", b"[]", b"{}", b'{"chart":{"error":null,"result":[]}}']
)
def test_fetch_yahoo_prices_handles_missing_quote_data(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    monkeypatch.setattr(
        market_prices, "urlopen", lambda *args, **kwargs: BytesIO(payload)
    )
    result = fetch_yahoo_prices({"SXRV": "SXRV.DE"}, {"SXRV": "EUR"})
    assert result.prices == {}
    assert result.unavailable == ["SXRV"]


def test_fetch_yahoo_prices_marks_missing_listing_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(*args: object, **kwargs: object) -> BytesIO:
        raise HTTPError("https://example.com", 404, "Not found", None, None)

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)
    result = fetch_yahoo_prices({"SXRV": "SXRV.DE"}, {"SXRV": "EUR"})
    assert result.prices == {}
    assert result.unavailable == ["SXRV"]


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("https://example.com", 429, "Limit reached", None, None),
        URLError("DNS lookup failed"),
        TimeoutError(),
    ],
)
def test_fetch_yahoo_prices_reports_request_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def fake_urlopen(*args: object, **kwargs: object) -> BytesIO:
        raise error

    monkeypatch.setattr(market_prices, "urlopen", fake_urlopen)
    with pytest.raises(MarketPriceError):
        fetch_yahoo_prices({"SXRV": "SXRV.DE"}, {"SXRV": "EUR"})


@pytest.mark.parametrize(
    "payload",
    [
        b"not JSON",
        b"x" * (market_prices.MAX_RESPONSE_BYTES + 1),
        b'{"chart":{"error":{"code":"Too Many Requests"},"result":null}}',
    ],
)
def test_fetch_yahoo_prices_rejects_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    monkeypatch.setattr(
        market_prices, "urlopen", lambda *args, **kwargs: BytesIO(payload)
    )
    with pytest.raises(MarketPriceError):
        fetch_yahoo_prices({"SXRV": "SXRV.DE"}, {"SXRV": "EUR"})
