from transactions.categorization import suggest_transaction_category


def test_suggest_transaction_category_returns_food_for_mercadona() -> None:
    category = suggest_transaction_category("MERCADONA CÑ DIEGO")

    assert category == "food"


def test_suggest_transaction_category_returns_food_for_simply_market() -> None:
    category = suggest_transaction_category("SIMPLY MARKET SARMI")

    assert category == "food"


def test_suggest_transaction_category_returns_food_for_mialcampo() -> None:
    category = suggest_transaction_category("MIALCAMPO GAMONAL")

    assert category == "food"


def test_suggest_transaction_category_returns_food_for_primaprix() -> None:
    category = suggest_transaction_category("PRIMAPRIX BURGOS IV")

    assert category == "food"


def test_suggest_transaction_category_returns_none_for_unknown_description() -> None:
    category = suggest_transaction_category("UNKNOWN MERCHANT")

    assert category is None


def test_suggest_transaction_category_returns_utilities_for_gana_energia() -> None:
    category = suggest_transaction_category("GANA ENERGIA LUZ 005084220000SDD000020408")

    assert category == "utilities"


def test_suggest_transaction_category_returns_subscriptions_for_spotify() -> None:
    category = suggest_transaction_category("SPOTIFY")

    assert category == "subscriptions"


def test_suggest_transaction_category_returns_subscriptions_for_overleaf() -> None:
    category = suggest_transaction_category("OVERLEAF EDITOR")

    assert category == "subscriptions"


def test_suggest_transaction_category_returns_subscriptions_for_cloudflare() -> None:
    category = suggest_transaction_category("CLOUDFLARE")

    assert category == "subscriptions"


def test_suggest_transaction_category_returns_leisure_for_odeon() -> None:
    category = suggest_transaction_category("ODEON MULTICINES BU")

    assert category == "leisure"


def test_suggest_transaction_category_returns_shopping_for_pccomponentes() -> None:
    category = suggest_transaction_category("PcComponentes")

    assert category == "shopping"


def test_suggest_transaction_category_returns_education_for_university() -> None:
    category = suggest_transaction_category("UNIVERSIDAD DE BURG")

    assert category == "education"


def test_suggest_transaction_category_returns_investment_for_revolut() -> None:
    category = suggest_transaction_category("Revolut**4660*")

    assert category == "investment"


def test_suggest_transaction_category_returns_investment_for_ibkr() -> None:
    category = suggest_transaction_category("TRANSFER TO IBKR")

    assert category == "investment"


def test_suggest_transaction_category_returns_housing_for_rent_payment() -> None:
    category = suggest_transaction_category("ALQUILER . BENEF: LUISA")

    assert category == "housing"


def test_suggest_transaction_category_returns_housing_for_rent_reimbursement() -> None:
    category = suggest_transaction_category(
        "BIZUM ABONO IBAI MOYA AROZ ALQUILER AGOSTO"
    )

    assert category == "housing"
