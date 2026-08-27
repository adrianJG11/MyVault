import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EODHD_EOD_URL = "https://eodhd.com/api/eod"
EODHD_SYMBOL_OVERRIDES = {
    ("AIL", "EUR"): "AI.PA",
}


class MarketPriceError(Exception):
    pass


@dataclass(frozen=True)
class MarketPriceResult:
    prices: dict[str, Decimal]
    unavailable: list[str]


def eodhd_symbol_for(ticker: str, currency: str) -> str | None:
    normalized_ticker = ticker.strip().upper()
    normalized_currency = currency.strip().upper()

    if normalized_currency == "USD":
        return f"{normalized_ticker}.US"

    return EODHD_SYMBOL_OVERRIDES.get((normalized_ticker, normalized_currency))


def _valid_price(value: object) -> Decimal | None:
    try:
        price = Decimal(str(value))
    except InvalidOperation, ValueError:
        return None

    return price if price.is_finite() and price > 0 else None


def fetch_eodhd_prices(
    symbols: Mapping[str, str],
    api_key: str,
) -> MarketPriceResult:
    normalized_symbols = {
        ticker.strip().upper(): provider_symbol.strip().upper()
        for ticker, provider_symbol in symbols.items()
    }

    if not normalized_symbols:
        return MarketPriceResult(prices={}, unavailable=[])

    today = datetime.now(UTC).date()
    query = urlencode(
        {
            "api_token": api_key,
            "fmt": "json",
            "from": (today - timedelta(days=14)).isoformat(),
            "to": today.isoformat(),
            "order": "d",
        }
    )
    prices: dict[str, Decimal] = {}
    unavailable: list[str] = []

    for ticker, provider_symbol in sorted(normalized_symbols.items()):
        request = Request(f"{EODHD_EOD_URL}/{provider_symbol}?{query}")

        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read())
        except HTTPError as error:
            if error.code == 404:
                unavailable.append(ticker)
                continue
            raise MarketPriceError("Market price request failed") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise MarketPriceError("Market price request failed") from error

        if isinstance(payload, Mapping):
            raise MarketPriceError("Market price provider returned an error")

        if not isinstance(payload, list) or not payload:
            unavailable.append(ticker)
            continue

        latest_price = (
            _valid_price(payload[0].get("close"))
            if isinstance(payload[0], Mapping)
            else None
        )

        if latest_price is None:
            unavailable.append(ticker)
        else:
            prices[ticker] = latest_price

    return MarketPriceResult(prices=prices, unavailable=unavailable)
