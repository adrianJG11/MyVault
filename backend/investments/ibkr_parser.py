import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, DecimalException
from hashlib import sha256
from typing import TYPE_CHECKING, BinaryIO
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from investments.revolut_importer import ParsedInvestmentActivity

MAX_IBKR_REPORT_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ParsedIBKRPrice:
    ticker: str
    currency: str
    price: Decimal
    as_of_date: date


class _ReportTreeBuilder(ElementTree.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("IBKR XML must not contain a document type")


def parse_flex_xml(source: BinaryIO) -> ElementTree.Element:
    payload = source.read(MAX_IBKR_REPORT_BYTES + 1)
    if len(payload) > MAX_IBKR_REPORT_BYTES:
        raise ValueError("IBKR report exceeds 10 MB")
    try:
        return ElementTree.fromstring(
            payload, parser=ElementTree.XMLParser(target=_ReportTreeBuilder())
        )
    except (ElementTree.ParseError, LookupError) as error:
        raise ValueError("Invalid IBKR report") from error


def parse_ibkr_xml(source: BinaryIO) -> list[ParsedInvestmentActivity]:
    activities, _ = parse_ibkr_report(source)
    return activities


def parse_ibkr_report(
    source: BinaryIO,
) -> tuple[list[ParsedInvestmentActivity], list[ParsedIBKRPrice]]:
    try:
        root = parse_flex_xml(source)
        if root.tag != "FlexQueryResponse":
            raise ValueError("Expected an IBKR report")

        trades = list(root.iter("Trade"))
        activities: list[ParsedInvestmentActivity] = []
        broker_accounts = {
            statement.attrib["accountId"].strip()
            for statement in root.iter("FlexStatement")
            if statement.attrib.get("accountId", "").strip()
        }
        if len(broker_accounts) > 1:
            raise ValueError("Expected one IBKR account per report")

        for trade in trades:
            if trade.attrib.get("assetCategory") != "STK":
                raise ValueError("Unsupported IBKR asset category")

            broker_account_id = trade.attrib.get("accountId", "").strip()
            trade_id = trade.attrib.get("tradeID", "").strip()
            ticker = trade.attrib.get("symbol", "").strip()
            currency = trade.attrib.get("currency", "").strip()
            quantity = Decimal(trade.attrib["quantity"])
            price = Decimal(trade.attrib["tradePrice"])
            fx_rate = Decimal(trade.attrib["fxRateToBase"])
            identity = json.dumps(
                ["ibkr", broker_account_id, trade_id], separators=(",", ":")
            )
            fingerprint = sha256(identity.encode(), usedforsecurity=False).hexdigest()

            if not broker_account_id or not trade_id:
                raise ValueError("Missing IBKR trade identity")
            broker_accounts.add(broker_account_id)
            if len(broker_accounts) > 1:
                raise ValueError("Expected one IBKR account per report")
            if not ticker or len(ticker) > 20:
                raise ValueError("Invalid ticker")
            if (
                len(currency) != 3
                or not currency.isascii()
                or not currency.isalpha()
                or not currency.isupper()
            ):
                raise ValueError("Invalid currency")
            if not quantity.is_finite() or quantity == 0:
                raise ValueError("Invalid quantity")
            if not price.is_finite() or price <= 0:
                raise ValueError("Invalid price")
            if not fx_rate.is_finite() or fx_rate <= 0:
                raise ValueError("Invalid FX rate")

            side = trade.attrib["buySell"]
            net_cash = Decimal(trade.attrib["netCash"])

            if not net_cash.is_finite():
                raise ValueError("Invalid net cash")

            if side == "BUY":
                if quantity <= 0:
                    raise ValueError("Expected positive quantity for a purchase")
                if net_cash >= 0:
                    raise ValueError("Expected negative cash for a purchase")
                activity_type = "BUY - MARKET"
                total_amount = -net_cash
            elif side == "SELL":
                if quantity >= 0:
                    raise ValueError("Expected negative quantity for a sale")
                quantity = -quantity
                activity_type = "SELL - MARKET"
                total_amount = net_cash
            else:
                raise ValueError("Unsupported trade side")

            occurred_at = (
                datetime.strptime(trade.attrib["dateTime"], "%Y%m%d;%H%M%S")
                .replace(tzinfo=ZoneInfo("America/New_York"))
                .astimezone(UTC)
            )

            activities.append(
                {
                    "ticker": ticker,
                    "activity_type": activity_type,
                    "quantity": quantity,
                    "price_per_share": price,
                    "total_amount": total_amount,
                    "currency": currency,
                    "fx_rate": fx_rate,
                    "occurred_at": occurred_at,
                    "import_fingerprint": fingerprint,
                }
            )

        prices: dict[str, ParsedIBKRPrice] = {}
        for position in root.iter("OpenPosition"):
            if position.attrib.get("assetCategory") != "STK":
                raise ValueError("Unsupported IBKR asset category")
            if position.attrib.get("levelOfDetail") != "SUMMARY":
                raise ValueError("IBKR open positions must use Summary detail")
            broker_account_id = position.attrib.get("accountId", "").strip()
            if not broker_account_id:
                raise ValueError("Missing IBKR position account")
            broker_accounts.add(broker_account_id)
            if len(broker_accounts) > 1:
                raise ValueError("Expected one IBKR account per report")

            ticker = position.attrib.get("symbol", "").strip()
            currency = position.attrib.get("currency", "").strip()
            if not ticker or len(ticker) > 20:
                raise ValueError("Invalid ticker")
            if (
                len(currency) != 3
                or not currency.isascii()
                or not currency.isalpha()
                or not currency.isupper()
            ):
                raise ValueError("Invalid currency")
            price = Decimal(position.attrib["markPrice"])
            if not price.is_finite() or price <= 0:
                raise ValueError("Invalid IBKR closing price")
            report_date = date.fromisoformat(position.attrib["reportDate"])
            if report_date > datetime.now(ZoneInfo("America/New_York")).date():
                raise ValueError("IBKR price report date is in the future")

            parsed_price = ParsedIBKRPrice(ticker, currency, price, report_date)
            previous = prices.get(ticker)
            if previous is not None:
                if previous.currency != currency:
                    raise ValueError("IBKR ticker uses multiple currencies")
                if previous.as_of_date == report_date and previous != parsed_price:
                    raise ValueError("Conflicting IBKR closing prices")
                if previous.as_of_date >= report_date:
                    continue
            prices[ticker] = parsed_price

        return activities, list(prices.values())
    except (KeyError, DecimalException) as error:
        raise ValueError("Invalid IBKR report") from error


if __name__ == "__main__":
    with open("ibkr_report.xml", "rb") as source:
        activities = parse_ibkr_xml(source)
    print("Activities parsed:", len(activities))
