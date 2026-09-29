from datetime import UTC, datetime
from decimal import Decimal
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
        quantity = Decimal(trade.attrib["quantity"])
        price = Decimal(trade.attrib["tradePrice"])

        if not quantity.is_finite() or quantity == 0:
            raise ValueError("Invalid quantity")
        if not price.is_finite() or price <= 0:
            raise ValueError("Invalid price")

        side = trade.attrib["buySell"]
        net_cash = Decimal(trade.attrib["netCash"])

        if not net_cash.is_finite():
            raise ValueError("Invalid net cash")

        if side == "BUY":
            if net_cash >= 0:
                raise ValueError("Expected negative cash for a purchase")
            activity_type = "BUY - MARKET"
            total_amount = -net_cash
        elif side == "SELL":
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
                "ticker": trade.attrib["symbol"],
                "activity_type": activity_type,
                "quantity": quantity,
                "price_per_share": price,
                "total_amount": total_amount,
                "currency": trade.attrib["currency"],
                "occurred_at": occurred_at,
            }
        )

    return activities


if __name__ == "__main__":
    with open("ibkr_report.xml", "rb") as source:
        activities = parse_ibkr_xml(source)
    print("Activities parsed:", len(activities))
