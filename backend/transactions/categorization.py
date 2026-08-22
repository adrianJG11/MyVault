def suggest_transaction_category(description: str) -> str | None:
    normalized_description = description.upper()

    if (
        "MERCADONA" in normalized_description
        or "SIMPLY MARKET" in normalized_description
    ):
        return "food"

    if "GANA ENERGIA" in normalized_description:
        return "utilities"

    if "SPOTIFY" in normalized_description:
        return "subscriptions"

    if "REVOLUT" in normalized_description or "IBKR" in normalized_description:
        return "investment"

    if "ALQUILER" in normalized_description:
        return "housing"

    return None
