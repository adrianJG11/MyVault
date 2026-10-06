# Imports and investments

Create or select a dedicated account before importing. Include the purchase
history needed to calculate your holdings and later sales.

## Ibercaja

In **Transactions**, expand **Import transactions** and upload an Ibercaja XLSX
export. MyVault reports new transactions and duplicates skipped. Existing data
is preserved when the workbook is invalid.

## Revolut

In **Investments**, expand **Import investment activity**, choose **Revolut CSV**,
and upload the investment-activity export. The columns must appear in this order:

```csv
Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate
```

The importer supports market purchases, market sales, dividends, cash top-ups,
and withdrawals. Include your first purchases in the initial import; overlapping
exports are safe when transaction details remain unchanged.

## IBKR investment imports

Create a dedicated IBKR account with `POST /accounts`. Configure an Activity
Flex Query in XML format with Trades at the Executions level and these fields:
`accountId`, `assetCategory`, `buySell`, `conid`, `currency`, `dateTime`,
`fxRateToBase`, `ibCommission`, `ibCommissionCurrency`, `netCash`, `quantity`,
`symbol`, `tradeID`, and `tradePrice`.

For closing prices, also enable **Open Positions** at **Summary** level and
include **Account ID**, **Asset Class**, **Symbol**, **Currency**, **Mark Price**,
**Report Date**, and **Level of Detail**. In XML these are `accountId`,
`assetCategory`, `symbol`, `currency`, `markPrice`, `reportDate`, and
`levelOfDetail`. IBKR's Mark Price is the closing price as of the report date,
not a live quote. See the [IBKR Open Positions field reference](https://www.ibkrguides.com/reportingreference/reportguide/open%20positionsfq.htm).

Upload a manually exported report through
`POST /accounts/{account_id}/imports/ibkr-investments` in
<http://127.0.0.1:8000/docs>. For example, from the repository root, replacing
`ACCOUNT_ID` with your local IBKR account's ID:

```bash
curl --fail-with-body \
  -F 'file=@ibkr_report.xml;type=application/xml' \
  http://127.0.0.1:8000/accounts/ACCOUNT_ID/imports/ibkr-investments
```

Duplicate detection uses the broker account and trade IDs. Reports that identify
the same execution differently cannot currently be reconciled automatically.

The response reports new activities and updated closing prices, for example
`{"imported": 2, "prices_updated": 2}`. Re-importing an unchanged report returns
`{"imported": 0, "prices_updated": 0}`. A newer report can update prices without
adding trades. Older or same-date IBKR prices cannot overwrite saved prices;
recent manual or external price updates are preserved. Inspect imported records
with `GET /investment-activities?account_id=ACCOUNT_ID` and FIFO results with
`GET /investment-summary?account_id=ACCOUNT_ID`.

Imports accept stock and ETF executions marked `STK`, one broker account per
report, and XML up to 10 MB. Trades are identified by broker account and trade
ID. Quantities are normalized to positive values; net cash already includes
fees. Execution times are interpreted as Eastern time and stored in UTC. FX
rates are retained, but summaries stay separate by trade currency. Import the
purchase history needed to calculate subsequent sales; short positions,
derivatives, dividends, corporate actions, and cash movements are not supported
by this IBKR importer.

Open Positions supplies prices, not replacement trade history. Each price must
match an imported ticker and currency in the selected account. Import the full
purchase and sale history first or include it in the same XML; later reports
may contain only Open Positions. Trades and prices are saved together, so an
invalid price or unmatched position leaves the import unchanged. Portfolio
quantities, cost basis, and P/L remain calculated from the imported trades.
The frontend shows the price source and IBKR report date next to each saved
price. SXRV and VWCE can therefore use IBKR closing prices without an external
quote provider. Dates can be `YYYYMMDD` or `YYYY-MM-DD`.

To download XML using the Flex Web Service, set `IBKR_FLEX_TOKEN` and
`IBKR_FLEX_QUERY_ID` in your private root `.env`, then run from the repository
root:

```bash
make ibkr-download
```

The downloader waits for generation, retries transient errors a limited number
of times, and validates the report before replacing `backend/ibkr_report.xml`.
The saved file has permissions `0600`. A failed download preserves the previous
file. To import this downloaded report with curl, use
`file=@backend/ibkr_report.xml;type=application/xml`. To import through the
frontend, select your IBKR account, open the Investments tab, expand
**Import investment activity**, choose **IBKR XML**, and upload the report.

## Investment share adjustments

Record a verified bonus-share or split event through
`PUT /accounts/{account_id}/investment-share-adjustments/{ticker}/{effective_date}`
in the local API documentation. Use a `YYYY-MM-DD` date and a body such as:

```json
{"multiplier": "1.1"}
```

For example, `1.1` means 10% more shares, `2` means twice as many, and `0.5`
means half as many. The event changes the open FIFO lots at the start of that
date in UTC, before trades at the same timestamp. The original purchases remain
unchanged, total cost is preserved, and later sales consume the adjusted lots.
The activity table displays the multiplier without a cash movement or FX rate.

Repeating the same account, ticker, date, and multiplier returns the existing
event. A different multiplier for that date is rejected. Future dates, events
without an open position, and adjustments incompatible with later sales are
also rejected. Broker imports continue to skip previously imported trades;
these adjustment events are recorded manually, not inferred from a CSV or XML.

This flow handles exact quantity multipliers. Cash in lieu of fractional shares,
mergers, spin-offs, and automatic corporate-action imports are not included.
Private reconciliation backups in `backend/.private-reconciliation/` are excluded
from Git and Docker builds. The migration refuses to remove the multiplier
column while share-adjustment events exist.

