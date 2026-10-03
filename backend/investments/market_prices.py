import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
YAHOO_SYMBOL_OVERRIDES = {
    ("AIL", "EUR"): "AI.PA",
    ("SXRV", "EUR"): "SXRV.DE",
    ("VWCE", "EUR"): "VWCE.DE",
}
MAX_RESPONSE_BYTES = 1_000_000


class MarketPriceError(Exception):
    pass


@dataclass(frozen=True)
class MarketQuote:
    price: Decimal
    quoted_at: datetime


@dataclass(frozen=True)
class MarketPriceResult:
    prices: dict[str, MarketQuote]
    unavailable: list[str]


def yahoo_symbol_for(ticker: str, currency: str) -> str | None:
    ticker = ticker.strip().upper()
    currency = currency.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.=-]{0,19}", ticker):
        return None
    if currency == "USD":
        return ticker
    return YAHOO_SYMBOL_OVERRIDES.get((ticker, currency))


def fetch_yahoo_prices(
    symbols: Mapping[str, str],
    currencies: Mapping[str, str],
) -> MarketPriceResult:
    prices: dict[str, MarketQuote] = {}
    unavailable: list[str] = []

    for ticker, provider_symbol in sorted(symbols.items()):
        request = Request(
            f"{YAHOO_CHART_URL}/{quote(provider_symbol, safe='')}?interval=1d&range=5d",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                raise MarketPriceError("Market price response too large")
            payload = json.loads(data, parse_float=Decimal)
        except HTTPError as error:
            if error.code == 404:
                unavailable.append(ticker)
                continue
            raise MarketPriceError("Market price request failed") from error
        except (URLError, OSError, ValueError) as error:
            raise MarketPriceError("Market price request failed") from error

        try:
            chart = payload["chart"]
            if chart["error"] is not None:
                raise MarketPriceError("Market price provider returned an error")
            meta = chart["result"][0]["meta"]
            if (
                meta["symbol"] != provider_symbol
                or meta["currency"] != currencies[ticker]
            ):
                raise ValueError("Quote does not match the listing and currency")
            price = Decimal(str(meta["regularMarketPrice"]))
            timestamp = meta["regularMarketTime"]
            if type(timestamp) is not int or timestamp <= 0:
                raise ValueError("Invalid quote timestamp")
            quoted_at = datetime.fromtimestamp(timestamp, UTC)
            if (
                not price.is_finite()
                or not 0 < price < Decimal("1e16")
                or quoted_at > datetime.now(UTC) + timedelta(minutes=5)
            ):
                raise ValueError("Invalid quote")
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            InvalidOperation,
            OverflowError,
            OSError,
        ):
            unavailable.append(ticker)
            continue

        prices[ticker] = MarketQuote(price=price, quoted_at=quoted_at)

    return MarketPriceResult(prices=prices, unavailable=unavailable)
