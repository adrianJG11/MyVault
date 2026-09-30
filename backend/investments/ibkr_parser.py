import json
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import BinaryIO
from xml.etree import ElementTree
from zoneinfo import ZoneInfo


def parse_ibkr_xml(source: BinaryIO) -> list[dict[str, str | Decimal | datetime]]:
    root = ElementTree.parse(source).getroot()
    if root.tag != "FlexQueryResponse":
        raise ValueError("Expected an IBKR report")

    trades = list(root.iter("Trade"))
    activities: list[dict[str, str | Decimal | datetime]] = []

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

    return activities


if __name__ == "__main__":
    with open("ibkr_report.xml", "rb") as source:
        activities = parse_ibkr_xml(source)
    print("Activities parsed:", len(activities))
