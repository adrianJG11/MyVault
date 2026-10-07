import {
  lazy,
  Suspense,
  type FormEvent,
  type ReactNode,
  useEffect,
  useState,
} from 'react'

import {
  clearInvestmentHistory,
  deleteInvestmentActivity,
  fetchInvestmentActivities,
  fetchInvestmentSummary,
  importInvestments,
  refreshInvestmentPrices,
  updateInvestmentPrice,
} from './api'
import type { InvestmentActivity, InvestmentSummary } from './types'

const INVESTMENT_ACTIVITIES_PER_PAGE = 10
const InvestmentCharts = lazy(() => import('./InvestmentCharts'))

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const dateFormatter = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' })

function formatMoney(value: string, currency: string) {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  }).format(Number(value))
}

function formatQuantity(value: string | null) {
  if (value === null) {
    return '—'
  }

  return Number(value).toLocaleString('en-GB', {
    maximumFractionDigits: 12,
  })
}

function amountClass(value: string | null) {
  if (value === null) {
    return undefined
  }

  return Number(value) >= 0 ? 'amount-positive' : 'amount-negative'
}

function formatPercent(value: string | null) {
  if (value === null) {
    return '—'
  }

  return `${Number(value).toLocaleString('en-GB', {
    maximumFractionDigits: 2,
  })}%`
}

function priceDraftsFrom(summary: InvestmentSummary) {
  return Object.fromEntries(
    summary.positions.map((position) => [
      position.ticker,
      position.current_price ?? '',
    ]),
  )
}

async function fetchInvestmentData(accountId: number) {
  const [activities, summary] = await Promise.all([
    fetchInvestmentActivities(accountId),
    fetchInvestmentSummary(accountId),
  ])
  return { activities, summary }
}

type InvestmentsPanelProps = {
  accountId: number
  accountName: string
}

export function InvestmentsPanel({ accountId, accountName }: InvestmentsPanelProps) {
  const [activities, setActivities] = useState<InvestmentActivity[]>([])
  const [summary, setSummary] = useState<InvestmentSummary>({
    positions: [],
    currencies: [],
  })
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [broker, setBroker] = useState<'revolut' | 'ibkr'>('revolut')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importMessage, setImportMessage] = useState<{
    text: string
    tone: 'success' | 'error'
  } | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [priceDrafts, setPriceDrafts] = useState<Record<string, string>>({})
  const [savingPriceTicker, setSavingPriceTicker] = useState<string | null>(
    null,
  )
  const [isRefreshingPrices, setIsRefreshingPrices] = useState(false)
  const [priceMessage, setPriceMessage] = useState<{
    text: string
    tone: 'success' | 'error'
  } | null>(null)
  const [showClosedPositions, setShowClosedPositions] = useState(false)
  const [deletingActivityId, setDeletingActivityId] = useState<number | null>(null)
  const [isClearingHistory, setIsClearingHistory] = useState(false)
  const [deletionMessage, setDeletionMessage] = useState<{
    text: string
    tone: 'success' | 'warning' | 'error'
  } | null>(null)
  const isDeleting = deletingActivityId !== null || isClearingHistory
  const isMutating = isDeleting || isImporting || isRefreshingPrices || savingPriceTicker !== null

  const totalPages = Math.max(
    1,
    Math.ceil(activities.length / INVESTMENT_ACTIVITIES_PER_PAGE),
  )
  const pageStart = (currentPage - 1) * INVESTMENT_ACTIVITIES_PER_PAGE
  const visibleActivities = activities.slice(
    pageStart,
    pageStart + INVESTMENT_ACTIVITIES_PER_PAGE,
  )
  const displayedPositions = showClosedPositions
    ? summary.positions
    : summary.positions.filter((position) => Number(position.quantity) > 0)

  useEffect(() => {
    async function loadInvestments() {
      try {
        const data = await fetchInvestmentData(accountId)
        setActivities(data.activities)
        setSummary(data.summary)
        setPriceDrafts(priceDraftsFrom(data.summary))
        setCurrentPage(1)
      } catch {
        setError('Could not load investment activities.')
      } finally {
        setIsLoading(false)
      }
    }

    void loadInvestments()
  }, [accountId])

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (selectedFile === null) {
      return
    }

    const form = event.currentTarget
    const file = selectedFile
    setIsImporting(true)
    setImportMessage(null)
    setPriceMessage(null)
    setDeletionMessage(null)

    try {
      const result = await importInvestments(accountId, file, broker)
      const data = await fetchInvestmentData(accountId)

      setActivities(data.activities)
      setSummary(data.summary)
      setPriceDrafts(priceDraftsFrom(data.summary))
      setCurrentPage(1)
      setImportMessage({
        text: `Imported ${result.imported} new investment activities.${result.prices_updated !== undefined ? ` Updated ${result.prices_updated} IBKR closing prices.` : ''}`,
        tone: 'success',
      })
      setSelectedFile(null)
      const fileInput =
        form.querySelector<HTMLInputElement>('input[type="file"]')
      if (fileInput) {
        fileInput.value = ''
      }
    } catch {
      setImportMessage({
        text: 'The investment import or activity refresh failed.',
        tone: 'error',
      })
    } finally {
      setIsImporting(false)
    }
  }

  async function handlePriceUpdate(
    event: FormEvent<HTMLFormElement>,
    ticker: string,
  ) {
    event.preventDefault()
    const price = priceDrafts[ticker]?.trim()

    if (!price) {
      return
    }

    setSavingPriceTicker(ticker)
    setPriceMessage(null)

    try {
      await updateInvestmentPrice(accountId, ticker, price)
      const refreshedSummary = await fetchInvestmentSummary(accountId)
      setSummary(refreshedSummary)
      setPriceDrafts(priceDraftsFrom(refreshedSummary))
      setPriceMessage({
        text: `Updated the current price for ${ticker}.`,
        tone: 'success',
      })
    } catch {
      setPriceMessage({
        text: `Could not update the current price for ${ticker}.`,
        tone: 'error',
      })
    } finally {
      setSavingPriceTicker(null)
    }
  }

  async function handlePriceRefresh() {
    setIsRefreshingPrices(true)
    setPriceMessage(null)

    try {
      const result = await refreshInvestmentPrices(accountId)
      const refreshedSummary = await fetchInvestmentSummary(accountId)
      setSummary(refreshedSummary)
      setPriceDrafts(priceDraftsFrom(refreshedSummary))

      const details = [
        result.unavailable.length > 0
          ? `No newer quote: ${result.unavailable.join(', ')}. Saved prices were kept.`
          : '',
        result.manual_only.length > 0
          ? `No external quote: ${result.manual_only.join(', ')}. Saved report or manual prices were kept.`
          : '',
      ]
        .filter(Boolean)
        .join(' ')
      setPriceMessage({
        text: `Updated ${result.updated.length} market prices.${details ? ` ${details}` : ''}`,
        tone: 'success',
      })
    } catch {
      setPriceMessage({
        text: 'Could not refresh market prices. Saved prices were not changed.',
        tone: 'error',
      })
    } finally {
      setIsRefreshingPrices(false)
    }
  }

  async function handleActivityDelete(activity: InvestmentActivity) {
    if (!window.confirm(
      `Delete ${activity.activity_type.toLowerCase()} for ${activity.ticker ?? 'this account'} on ${dateTimeFormatter.format(new Date(activity.occurred_at))} in "${accountName}"?\n\nThis removes the record from MyVault. Importing its original report can restore it.`,
    )) return
    setDeletingActivityId(activity.id)
    setDeletionMessage(null)
    setImportMessage(null)
    setPriceMessage(null)
    try {
      await deleteInvestmentActivity(accountId, activity.id)
      setDeletionMessage({ text: 'Investment activity deleted.', tone: 'success' })
      try {
        const data = await fetchInvestmentData(accountId)
        setActivities(data.activities)
        setSummary(data.summary)
        setPriceDrafts(priceDraftsFrom(data.summary))
        setCurrentPage(1)
        setError(null)
      } catch {
        setDeletionMessage({
          text: 'Activity deleted, but the view could not refresh. Reload the page.',
          tone: 'warning',
        })
      }
    } catch (error) {
      setDeletionMessage({
        text: error instanceof Error ? error.message : 'Could not confirm deletion. Reload the page.',
        tone: 'error',
      })
    } finally {
      setDeletingActivityId(null)
    }
  }

  async function handleHistoryClear() {
    if (!window.confirm(
      `Clear all investment history for "${accountName}"?\n\nThis deletes trades, dividends, cash movements, manual share adjustments, and saved prices. Other accounts and bank transactions are kept.\n\nImport complete trade history again afterward. Manual share adjustments must be recorded again separately.`,
    )) return
    setIsClearingHistory(true)
    setDeletionMessage(null)
    setImportMessage(null)
    setPriceMessage(null)
    try {
      await clearInvestmentHistory(accountId)
      setActivities([])
      setSummary({ positions: [], currencies: [] })
      setPriceDrafts({})
      setCurrentPage(1)
      setError(null)
      setDeletionMessage({ text: 'Investment history and saved prices cleared for this account.', tone: 'success' })
    } catch (error) {
      setDeletionMessage({
        text: error instanceof Error ? error.message : 'Could not confirm the reset. Reload the page.',
        tone: 'error',
      })
    } finally {
      setIsClearingHistory(false)
    }
  }

  let content: ReactNode

  if (isLoading) {
    content = (
      <p className="notice notice-info" role="status">
        Loading investment activities...
      </p>
    )
  } else if (error) {
    content = (
      <p className="notice notice-error" role="alert">
        {error}
      </p>
    )
  } else {
    content = (
      <section className="investment-overview" aria-label="Investment overview">
        {summary.currencies.length > 0 && (
          <div className="investment-performance">
            <header className="section-header">
              <div>
                <h2>Your investments at a glance</h2>
                <p>
                  Cost, value, and results from your imported trades. Each
                  currency is shown separately.
                </p>
              </div>

              <div className="investment-actions">
                <button
                  type="button"
                  disabled={isMutating}
                  onClick={() => void handlePriceRefresh()}
                >
                  {isRefreshingPrices
                    ? 'Refreshing...'
                    : 'Refresh market prices'}
                </button>
              </div>
            </header>

            {summary.currencies.map((currencySummary) => (
              <div
                className="currency-performance"
                key={currencySummary.currency}
              >
                <div className="currency-heading">
                  <h3>{currencySummary.currency} portfolio</h3>
                  <span>
                    {currencySummary.total_open_positions} open positions ·{' '}
                    {currencySummary.priced_positions} with prices
                  </span>
                </div>

                {currencySummary.priced_positions <
                  currencySummary.total_open_positions && (
                  <p className="missing-prices" role="status">
                    Add prices for all open positions to calculate the complete
                    market value and total result.
                  </p>
                )}

                <div className="summary investment-summary">
                  <div className="summary-card">
                    <span>Remaining cost</span>
                    <strong>
                      {formatMoney(
                        currencySummary.remaining_cost,
                        currencySummary.currency,
                      )}
                    </strong>
                    <small>Cost of your open holdings</small>
                  </div>

                  <div className="summary-card">
                    <span>Market value</span>
                    <strong>
                      {currencySummary.market_value === null
                        ? 'Missing prices'
                        : formatMoney(
                            currencySummary.market_value,
                            currencySummary.currency,
                          )}
                    </strong>
                    <small>At the saved prices</small>
                  </div>

                  <div className="summary-card">
                    <span>Unrealized P/L</span>
                    <strong
                      className={amountClass(currencySummary.unrealized_pl)}
                    >
                      {currencySummary.unrealized_pl === null
                        ? '—'
                        : formatMoney(
                            currencySummary.unrealized_pl,
                            currencySummary.currency,
                          )}
                    </strong>
                    <small>Open positions</small>
                  </div>

                  <div className="summary-card">
                    <span>Realized P/L</span>
                    <strong
                      className={amountClass(currencySummary.realized_pl)}
                    >
                      {formatMoney(
                        currencySummary.realized_pl,
                        currencySummary.currency,
                      )}
                    </strong>
                    <small>Completed sales, using FIFO</small>
                  </div>

                  <div className="summary-card">
                    <span>Dividends</span>
                    <strong className={amountClass(currencySummary.dividends)}>
                      {formatMoney(
                        currencySummary.dividends,
                        currencySummary.currency,
                      )}
                    </strong>
                    <small>Imported dividend payments</small>
                  </div>

                  <div className="summary-card summary-card-highlight">
                    <span>Total result</span>
                    <strong
                      className={amountClass(currencySummary.total_result)}
                    >
                      {currencySummary.total_result === null
                        ? '—'
                        : formatMoney(
                            currencySummary.total_result,
                            currencySummary.currency,
                          )}
                    </strong>
                    <small>Realized + unrealized + dividends</small>
                  </div>
                </div>

                <Suspense
                  fallback={
                    <p className="chart-card" role="status">
                      Loading portfolio charts…
                    </p>
                  }
                >
                  <InvestmentCharts
                    positions={summary.positions}
                    currency={currencySummary.currency}
                    marketValue={currencySummary.market_value}
                  />
                </Suspense>
              </div>
            ))}

            <div className="positions-header">
              <h2>Your holdings</h2>

              <label>
                <input
                  type="checkbox"
                  checked={showClosedPositions}
                  onChange={(event) =>
                    setShowClosedPositions(event.target.checked)
                  }
                />
                Show closed positions
              </label>
            </div>

            {priceMessage && (
              <p
                className={`notice notice-${priceMessage.tone}`}
                role={priceMessage.tone === 'error' ? 'alert' : 'status'}
              >
                {priceMessage.text}
              </p>
            )}

            <div className="positions-grid">
              {displayedPositions.length === 0 && (
                <div className="empty-state">
                  <h3>No open holdings</h3>
                  <p>
                    {summary.positions.length > 0
                      ? 'Show closed positions to review your previous holdings.'
                      : 'Import investment activity to see your holdings here.'}
                  </p>
                </div>
              )}
              {displayedPositions.map((position) => (
                <article className="position-card" key={position.ticker}>
                  <header className="position-card-header">
                    <div className="position-identity">
                      <span className="holding-mark" aria-hidden="true">
                        {position.ticker.slice(0, 2)}
                      </span>
                      <div>
                        <h3>{position.ticker}</h3>
                        <span className="position-currency">
                          {position.currency} ·{' '}
                          {formatQuantity(position.quantity)} shares
                        </span>
                      </div>
                    </div>

                    <div className="position-total">
                      <span>Total result</span>
                      <strong className={amountClass(position.total_result)}>
                        {position.total_result === null
                          ? '—'
                          : formatMoney(
                              position.total_result,
                              position.currency,
                            )}
                      </strong>
                      <small>Including dividends</small>
                    </div>
                  </header>

                  <dl className="position-metrics">
                    <div>
                      <dt>Cost basis</dt>
                      <dd>
                        {formatMoney(
                          position.remaining_cost,
                          position.currency,
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Market value</dt>
                      <dd>
                        {position.market_value === null
                          ? '—'
                          : formatMoney(
                              position.market_value,
                              position.currency,
                            )}
                      </dd>
                    </div>
                    <div>
                      <dt>Unrealized P/L</dt>
                      <dd className={amountClass(position.unrealized_pl)}>
                        {position.unrealized_pl === null
                          ? '—'
                          : `${formatMoney(
                              position.unrealized_pl,
                              position.currency,
                            )} (${formatPercent(
                              position.unrealized_return_percent,
                            )})`}
                      </dd>
                    </div>
                    <div>
                      <dt>Realized P/L</dt>
                      <dd className={amountClass(position.realized_pl)}>
                        {formatMoney(position.realized_pl, position.currency)}
                      </dd>
                    </div>
                    <div>
                      <dt>Dividends</dt>
                      <dd className={amountClass(position.dividends)}>
                        {formatMoney(position.dividends, position.currency)}
                      </dd>
                    </div>
                  </dl>

                  <div className="position-price">
                    <span>
                      Saved price ({position.currency})
                      {position.price_source === 'ibkr' &&
                      position.price_as_of ? (
                        <small className="price-date">
                          IBKR closing price · as of{' '}
                          {dateFormatter.format(
                            new Date(`${position.price_as_of}T00:00:00`),
                          )}
                        </small>
                      ) : position.price_source === 'yahoo' &&
                        position.price_quoted_at ? (
                        <small className="price-date">
                          Yahoo quote ·{' '}
                          {position.currency === 'EUR'
                            ? '15 min delayed'
                            : 'may be delayed'}{' '}
                          · as of{' '}
                          {dateTimeFormatter.format(
                            new Date(position.price_quoted_at),
                          )}
                        </small>
                      ) : position.price_updated_at ? (
                        <small className="price-date">
                          {position.price_source === 'manual'
                            ? 'Manual price'
                            : 'Saved price'}{' '}
                          · saved{' '}
                          {dateTimeFormatter.format(
                            new Date(position.price_updated_at),
                          )}
                        </small>
                      ) : null}
                    </span>
                    {Number(position.quantity) > 0 ? (
                      <form
                        className="price-form"
                        onSubmit={(event) =>
                          handlePriceUpdate(event, position.ticker)
                        }
                      >
                        <input
                          type="number"
                          min="0.00000001"
                          step="any"
                          required
                          aria-label={`Saved price for ${position.ticker} in ${position.currency}`}
                          value={priceDrafts[position.ticker] ?? ''}
                          onChange={(event) =>
                            setPriceDrafts((drafts) => ({
                              ...drafts,
                              [position.ticker]: event.target.value,
                            }))
                          }
                        />
                        <button
                          type="submit"
                          disabled={isMutating}
                        >
                          {savingPriceTicker === position.ticker
                            ? 'Saving...'
                            : 'Save'}
                        </button>
                      </form>
                    ) : (
                      <strong>Closed position</strong>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}

        <div className="table-header">
          <h2>Activity history</h2>

          <p>
            {activities.length === 0
              ? 'No investment activities found.'
              : `Showing ${pageStart + 1}–${Math.min(
                  pageStart + INVESTMENT_ACTIVITIES_PER_PAGE,
                  activities.length,
                )} of ${activities.length} investment activities.`}
          </p>
        </div>

        {activities.length === 0 ? (
          <div className="empty-state">
            <h3>No investment activity yet</h3>
            <p>
              Import a Revolut CSV or IBKR XML report to start building your
              portfolio view.
            </p>
          </div>
        ) : (
          <div
            className="table-container investment-activity-table"
            tabIndex={0}
            role="region"
            aria-label="Investment activity history"
          >
            <table>
              <caption className="sr-only">
                Investment activity and share adjustments, with amounts in each
                currency
              </caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Type</th>
                  <th scope="col">Ticker</th>
                  <th scope="col">Quantity</th>
                  <th scope="col">Price</th>
                  <th scope="col">Total</th>
                  <th scope="col">FX rate</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>

              <tbody>
                {visibleActivities.map((activity) => (
                  <tr key={activity.id}>
                    <td>
                      {dateTimeFormatter.format(new Date(activity.occurred_at))}
                    </td>
                    <td className="activity-type">
                      {activity.activity_type.replaceAll('_', ' ')}
                    </td>
                    <td className="activity-ticker">
                      {activity.ticker ?? '—'}
                    </td>
                    <td data-label="Quantity">
                      {activity.activity_type === 'SHARE ADJUSTMENT'
                        ? `×${formatQuantity(activity.quantity_multiplier)} shares`
                        : formatQuantity(activity.quantity)}
                    </td>
                    <td data-label="Price">
                      {activity.price_per_share === null
                        ? '—'
                        : formatMoney(
                            activity.price_per_share,
                            activity.currency,
                          )}
                    </td>
                    <td className={amountClass(activity.total_amount)}>
                      {activity.activity_type === 'SHARE ADJUSTMENT'
                        ? '—'
                        : formatMoney(activity.total_amount, activity.currency)}
                    </td>
                    <td data-label="FX rate">
                      {activity.activity_type === 'SHARE ADJUSTMENT'
                        ? '—'
                        : formatQuantity(activity.fx_rate)}
                    </td>
                    <td className="activity-actions">
                      <button
                        type="button"
                        className="button-danger"
                        aria-label={`Delete ${activity.activity_type.toLowerCase()} for ${activity.ticker ?? 'this account'} on ${dateTimeFormatter.format(new Date(activity.occurred_at))}`}
                        disabled={isMutating}
                        onClick={() => void handleActivityDelete(activity)}
                      >
                        {deletingActivityId === activity.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <nav className="pagination" aria-label="Investment activity pages">
            <button
              type="button"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((page) => page - 1)}
            >
              Previous
            </button>

            <span>
              Page {currentPage} of {totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((page) => page + 1)}
            >
              Next
            </button>
          </nav>
        )}
      </section>
    )
  }

  return (
    <>
      <details className="import-panel">
        <summary>Import investment activity</summary>

        <form onSubmit={handleImport}>
          <p>
            Upload{' '}
            {broker === 'ibkr'
              ? 'an IBKR Flex XML report'
              : 'a Revolut investment CSV'}{' '}
            for the selected account.
          </p>
          {broker === 'ibkr' && (
            <p>
              Include Open Positions at Summary level with Account ID, Asset
              Class, Symbol, Currency, Mark Price, Report Date, and Level of
              Detail to import closing prices. Include the purchase history for
              your holdings.
            </p>
          )}

          <div className="import-controls">
            <label htmlFor="investment-broker">Broker</label>
            <select
              id="investment-broker"
              value={broker}
              disabled={isImporting}
              onChange={(event) => {
                setBroker(event.target.value === 'ibkr' ? 'ibkr' : 'revolut')
                setSelectedFile(null)
                setImportMessage(null)
              }}
            >
              <option value="revolut">Revolut CSV</option>
              <option value="ibkr">IBKR XML</option>
            </select>
            <label htmlFor="investment-file">
              {broker === 'ibkr'
                ? 'IBKR Flex XML report'
                : 'Revolut investment CSV'}
            </label>
            <input
              key={broker}
              id="investment-file"
              type="file"
              accept={
                broker === 'ibkr'
                  ? '.xml,application/xml,text/xml'
                  : '.csv,text/csv'
              }
              disabled={isImporting}
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null)
                setImportMessage(null)
              }}
            />
            <button
              type="submit"
              disabled={selectedFile === null || isMutating}
            >
              {isImporting ? 'Importing...' : 'Import'}
            </button>
          </div>
        </form>
      </details>

      <div className="history-actions">
        <p>Start again with a new export by clearing this account’s investment history.</p>
        <button
          type="button"
          className="button-danger"
          disabled={isLoading || isMutating || (activities.length === 0 && !error)}
          onClick={() => void handleHistoryClear()}
        >
          {isClearingHistory ? 'Clearing...' : 'Clear investment history'}
        </button>
      </div>

      {deletionMessage && (
        <p className={`notice notice-${deletionMessage.tone}`} role={deletionMessage.tone === 'error' ? 'alert' : 'status'}>
          {deletionMessage.text}
        </p>
      )}

      <p className="investment-price-note">
        Prices are saved snapshots. Supported European Yahoo listings have a
        15-minute delay; you can also save prices manually.
      </p>

      {importMessage && (
        <p
          className={`notice notice-${importMessage.tone}`}
          role={importMessage.tone === 'error' ? 'alert' : 'status'}
        >
          {importMessage.text}
        </p>
      )}
      {content}
    </>
  )
}
