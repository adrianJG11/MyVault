import { type FormEvent, type ReactNode, useEffect, useState } from 'react'

import {
  fetchInvestmentActivities,
  fetchInvestmentSummary,
  importRevolutInvestments,
  refreshInvestmentPrices,
  updateInvestmentPrice,
} from './api'
import type { InvestmentActivity, InvestmentSummary } from './types'

const INVESTMENT_ACTIVITIES_PER_PAGE = 10

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function formatMoney(value: string, currency: string) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
  }).format(Number(value))
}

function formatQuantity(value: string | null) {
  if (value === null) {
    return '—'
  }

  return Number(value).toLocaleString('es-ES', {
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

  return `${Number(value).toLocaleString('es-ES', {
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
}

export function InvestmentsPanel({ accountId }: InvestmentsPanelProps) {
  const [activities, setActivities] = useState<InvestmentActivity[]>([])
  const [summary, setSummary] = useState<InvestmentSummary>({
    positions: [],
    currencies: [],
  })
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [priceDrafts, setPriceDrafts] = useState<Record<string, string>>({})
  const [savingPriceTicker, setSavingPriceTicker] = useState<string | null>(null)
  const [isRefreshingPrices, setIsRefreshingPrices] = useState(false)
  const [priceMessage, setPriceMessage] = useState<string | null>(null)
  const [showClosedPositions, setShowClosedPositions] = useState(false)

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

    try {
      const result = await importRevolutInvestments(accountId, file)
      const data = await fetchInvestmentData(accountId)

      setActivities(data.activities)
      setSummary(data.summary)
      setPriceDrafts(priceDraftsFrom(data.summary))
      setCurrentPage(1)
      setImportMessage(
        `Imported ${result.imported} new investment activities.`,
      )
      setSelectedFile(null)
      form.reset()
    } catch {
      setImportMessage('The investment import or activity refresh failed.')
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
      setPriceMessage(`Updated the current price for ${ticker}.`)
    } catch {
      setPriceMessage(`Could not update the current price for ${ticker}.`)
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
          ? `Unavailable: ${result.unavailable.join(', ')}.`
          : '',
        result.manual_only.length > 0
          ? `Manual only: ${result.manual_only.join(', ')}.`
          : '',
      ]
        .filter(Boolean)
        .join(' ')
      setPriceMessage(
        `Updated ${result.updated.length} market prices.${details ? ` ${details}` : ''}`,
      )
    } catch {
      setPriceMessage(
        'Could not refresh market prices. Saved manual prices were not changed.',
      )
    } finally {
      setIsRefreshingPrices(false)
    }
  }

  let content: ReactNode

  if (isLoading) {
    content = <p>Loading investment activities...</p>
  } else if (error) {
    content = <p role="alert">{error}</p>
  } else {
    content = (
      <section>
        {summary.currencies.length > 0 && (
          <div className="investment-performance">
            <h2>Investment performance</h2>
            <p>
              Results use FIFO and stay separated by currency. Supported USD
              prices can be refreshed on demand; manual prices remain available.
            </p>

            <div className="investment-actions">
              <button
                type="button"
                disabled={isRefreshingPrices}
                onClick={() => void handlePriceRefresh()}
              >
                {isRefreshingPrices ? 'Refreshing...' : 'Refresh market prices'}
              </button>
            </div>

            {summary.currencies.map((currencySummary) => (
              <div
                className="currency-performance"
                key={currencySummary.currency}
              >
                <h3>{currencySummary.currency}</h3>

                {currencySummary.priced_positions <
                  currencySummary.total_open_positions && (
                  <p className="missing-prices" role="status">
                    Add prices for all open positions to calculate the complete
                    market value and total result.
                  </p>
                )}

                <div className="summary">
                  <div className="summary-card">
                    <span>Remaining cost</span>
                    <strong>
                      {formatMoney(
                        currencySummary.remaining_cost,
                        currencySummary.currency,
                      )}
                    </strong>
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
                  </div>

                  <div className="summary-card">
                    <span>Realized P/L</span>
                    <strong className={amountClass(currencySummary.realized_pl)}>
                      {formatMoney(
                        currencySummary.realized_pl,
                        currencySummary.currency,
                      )}
                    </strong>
                  </div>

                  <div className="summary-card">
                    <span>Dividends</span>
                    <strong className={amountClass(currencySummary.dividends)}>
                      {formatMoney(
                        currencySummary.dividends,
                        currencySummary.currency,
                      )}
                    </strong>
                  </div>

                  <div className="summary-card">
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
                  </div>
                </div>
              </div>
            ))}

            <div className="positions-header">
              <h2>Positions</h2>

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

            {priceMessage && <p role="status">{priceMessage}</p>}

            <div className="positions-grid">
              {displayedPositions.map((position) => (
                <article className="position-card" key={position.ticker}>
                  <header className="position-card-header">
                    <div>
                      <h3>{position.ticker}</h3>
                      <span className="position-currency">
                        {position.currency} · {formatQuantity(position.quantity)}{' '}
                        shares
                      </span>
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
                      {position.unrealized_return_percent !== null && (
                        <small
                          className={amountClass(
                            position.unrealized_return_percent,
                          )}
                        >
                          Unrealized return:{' '}
                          {formatPercent(position.unrealized_return_percent)}
                        </small>
                      )}
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
                    <span>Current price ({position.currency})</span>
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
                          aria-label={`Current price for ${position.ticker} in ${position.currency}`}
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
                          disabled={savingPriceTicker === position.ticker}
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

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Ticker</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Total</th>
                <th>FX rate</th>
              </tr>
            </thead>

            <tbody>
              {visibleActivities.map((activity) => (
                <tr key={activity.id}>
                  <td>
                    {dateTimeFormatter.format(new Date(activity.occurred_at))}
                  </td>
                  <td>{activity.activity_type}</td>
                  <td>{activity.ticker ?? '—'}</td>
                  <td>{formatQuantity(activity.quantity)}</td>
                  <td>
                    {activity.price_per_share === null
                      ? '—'
                      : formatMoney(activity.price_per_share, activity.currency)}
                  </td>
                  <td>
                    {formatMoney(activity.total_amount, activity.currency)}
                  </td>
                  <td>{formatQuantity(activity.fx_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

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
      <form className="import-panel" onSubmit={handleImport}>
        <h2>Import investment activity</h2>
        <p>Upload a Revolut investment CSV for the selected account.</p>

        <div className="import-controls">
          <label htmlFor="revolut-investments-file">
            Revolut investment CSV
          </label>
          <input
            id="revolut-investments-file"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              setSelectedFile(event.target.files?.[0] ?? null)
              setImportMessage(null)
            }}
          />
          <button
            type="submit"
            disabled={selectedFile === null || isImporting}
          >
            {isImporting ? 'Importing...' : 'Import'}
          </button>
        </div>
      </form>

      {importMessage && <p role="status">{importMessage}</p>}
      {content}
    </>
  )
}
