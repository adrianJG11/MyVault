import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TWELVE_DATA_PRICE_URL = "https://api.twelvedata.com/price"


class MarketPriceError(Exception):
    pass


@dataclass(frozen=True)
class MarketPriceResult:
    prices: dict[str, Decimal]
    unavailable: list[str]


def _valid_price(value: object) -> Decimal | None:
    try:
        price = Decimal(str(value))
    except InvalidOperation, ValueError:
        return None

    return price if price.is_finite() and price > 0 else None


def fetch_twelve_data_prices(
    symbols: Sequence[str],
    api_key: str,
) -> MarketPriceResult:
    normalized_symbols = sorted({symbol.strip().upper() for symbol in symbols})

    if not normalized_symbols:
        return MarketPriceResult(prices={}, unavailable=[])

    query = urlencode({"symbol": ",".join(normalized_symbols)})
    request = Request(
        f"{TWELVE_DATA_PRICE_URL}?{query}",
        headers={"Authorization": f"apikey {api_key}"},
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise MarketPriceError("Market price request failed") from error

    if not isinstance(payload, Mapping) or payload.get("status") == "error":
        raise MarketPriceError("Market price provider returned an error")

    if len(normalized_symbols) == 1 and "price" in payload:
        payload_by_symbol: Mapping[str, object] = {normalized_symbols[0]: payload}
    else:
        payload_by_symbol = payload

    prices: dict[str, Decimal] = {}
    unavailable: list[str] = []

    for symbol in normalized_symbols:
        symbol_payload = payload_by_symbol.get(symbol)
        price = (
            _valid_price(symbol_payload.get("price"))
            if isinstance(symbol_payload, Mapping)
            else None
        )

        if price is None:
            unavailable.append(symbol)
        else:
            prices[symbol] = price

    return MarketPriceResult(prices=prices, unavailable=unavailable)
