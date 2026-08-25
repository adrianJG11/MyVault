def suggest_transaction_category(description: str) -> str | None:
    normalized_description = description.upper()

    if (
        "MERCADONA" in normalized_description
        or "SIMPLY MARKET" in normalized_description
        or "MIALCAMPO" in normalized_description
        or "PRIMAPRIX" in normalized_description
    ):
        return "food"

    if "GANA ENERGIA" in normalized_description:
        return "utilities"

    if (
        "SPOTIFY" in normalized_description
        or "OVERLEAF" in normalized_description
        or "CLOUDFLARE" in normalized_description
    ):
        return "subscriptions"

    if "ODEON" in normalized_description:
        return "leisure"

    if "PCCOMPONENTES" in normalized_description:
        return "shopping"

    if "UNIVERSIDAD DE BURG" in normalized_description:
        return "education"

    if "REVOLUT" in normalized_description or "IBKR" in normalized_description:
        return "investment"

    if "ALQUILER" in normalized_description:
        return "housing"

    return None
