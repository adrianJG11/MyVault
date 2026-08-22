import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useState,
} from 'react'

// REVIEW: Explain why dates and Decimal amounts arrive as strings from the API.
type Transaction = {
  id: number
  account_id: number
  operation_date: string
  value_date: string
  amount: string
  balance_after: string
  bank_concept: string
  description: string
  category: string | null
}

type Account = {
  id: number
  name: string
  bank_name: string
  currency: string
}

type ImportResult = {
  imported: number
}

type InvestmentActivity = {
  id: number
  account_id: number
  occurred_at: string
  ticker: string | null
  activity_type: string
  quantity: string | null
  price_per_share: string | null
  total_amount: string
  currency: string
  fx_rate: string
}

type InvestmentPosition = {
  ticker: string
  currency: string
  quantity: string
  remaining_cost: string
  current_price: string | null
  market_value: string | null
  unrealized_pl: string | null
  unrealized_return_percent: string | null
  realized_pl: string
  dividends: string
  total_result: string | null
}

type InvestmentCurrencySummary = {
  currency: string
  remaining_cost: string
  market_value: string | null
  unrealized_pl: string | null
  realized_pl: string
  dividends: string
  total_result: string | null
  priced_positions: number
  total_open_positions: number
}

type InvestmentSummary = {
  positions: InvestmentPosition[]
  currencies: InvestmentCurrencySummary[]
}

type InvestmentPriceRefreshResult = {
  updated: string[]
  unavailable: string[]
  manual_only: string[]
}

type ActiveTab = 'transactions' | 'investments'

const euroFormatter = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
})

const TRANSACTIONS_PER_PAGE = 10
const INVESTMENT_ACTIVITIES_PER_PAGE = 10

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function formatDate(value: string) {
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

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

async function fetchTransactions(
  accountId: number,
  dateFrom: string,
  dateTo: string,
): Promise<Transaction[]> {
  const params = new URLSearchParams({
    account_id: String(accountId),
  })

  if (dateFrom) {
    params.set('date_from', dateFrom)
  }

  if (dateTo) {
    params.set('date_to', dateTo)
  }

  const response = await fetch(`/api/transactions?${params}`)

  if (!response.ok) {
    throw new Error('Request failed')
  }

  return (await response.json()) as Transaction[]
}

async function fetchInvestmentActivities(
  accountId: number,
): Promise<InvestmentActivity[]> {
  const response = await fetch(
    `/api/investment-activities?account_id=${accountId}`,
  )

  if (!response.ok) {
    throw new Error('Request failed')
  }

  return (await response.json()) as InvestmentActivity[]
}

async function fetchInvestmentSummary(
  accountId: number,
): Promise<InvestmentSummary> {
  const response = await fetch(`/api/investment-summary?account_id=${accountId}`)

  if (!response.ok) {
    throw new Error('Request failed')
  }

  return (await response.json()) as InvestmentSummary
}

function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('transactions')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [error, setError] = useState<string | null>(null)
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [investmentActivities, setInvestmentActivities] = useState<
    InvestmentActivity[]
  >([])
  const [investmentSummary, setInvestmentSummary] = useState<InvestmentSummary>(
    { positions: [], currencies: [] },
  )
  const [investmentError, setInvestmentError] = useState<string | null>(null)
  const [isInvestmentsLoading, setIsInvestmentsLoading] = useState(true)
  const [selectedInvestmentFile, setSelectedInvestmentFile] =
    useState<File | null>(null)
  const [investmentImportMessage, setInvestmentImportMessage] = useState<
    string | null
  >(null)
  const [isInvestmentImporting, setIsInvestmentImporting] = useState(false)
  const [investmentPage, setInvestmentPage] = useState(1)
  const [priceDrafts, setPriceDrafts] = useState<Record<string, string>>({})
  const [savingPriceTicker, setSavingPriceTicker] = useState<string | null>(null)
  const [isRefreshingPrices, setIsRefreshingPrices] = useState(false)
  const [priceMessage, setPriceMessage] = useState<string | null>(null)

  const totalPages = Math.max(
    1,
    Math.ceil(transactions.length / TRANSACTIONS_PER_PAGE),
  )
  const pageStart = (currentPage - 1) * TRANSACTIONS_PER_PAGE
  const visibleTransactions = transactions.slice(
    pageStart,
    pageStart + TRANSACTIONS_PER_PAGE,
  )
  const investmentTotalPages = Math.max(
    1,
    Math.ceil(
      investmentActivities.length / INVESTMENT_ACTIVITIES_PER_PAGE,
    ),
  )
  const investmentPageStart =
    (investmentPage - 1) * INVESTMENT_ACTIVITIES_PER_PAGE
  const visibleInvestmentActivities = investmentActivities.slice(
    investmentPageStart,
    investmentPageStart + INVESTMENT_ACTIVITIES_PER_PAGE,
  )

  const moneyIn = transactions
    .filter((transaction) => Number(transaction.amount) > 0)
    .reduce(
      (total, transaction) => total + Number(transaction.amount),
      0,
    )

  const moneyOut = transactions
    .filter((transaction) => Number(transaction.amount) < 0)
    .reduce(
      (total, transaction) =>
        total + Math.abs(Number(transaction.amount)),
      0,
    )

  const net = moneyIn - moneyOut

  const monthlyTotalsByMonth = new Map<
    string,
    { moneyIn: number; moneyOut: number }
  >()

  for (const transaction of transactions) {
    const month = transaction.operation_date.slice(0, 7)
    const amount = Number(transaction.amount)

    const totals = monthlyTotalsByMonth.get(month) ?? {
      moneyIn: 0,
      moneyOut: 0,
    }

    if (amount >= 0) {
      totals.moneyIn += amount
    } else {
      totals.moneyOut += Math.abs(amount)
    }

    monthlyTotalsByMonth.set(month, totals)
  }

  const monthlyTotals = [...monthlyTotalsByMonth.entries()]
    .map(([month, totals]) => ({
      month,
      ...totals,
    }))
    .sort((first, second) => first.month.localeCompare(second.month))

  const largestMonthlyAmount = Math.max(
    1,
    ...monthlyTotals.flatMap((month) => [month.moneyIn, month.moneyOut]),
  )

  // REVIEW: Explain why accounts are loaded only when the component mounts.
  useEffect(() => {
    async function loadAccounts() {
      try {
        const response = await fetch('/api/accounts')

        if (!response.ok) {
          throw new Error('Request failed')
        }

        const data = (await response.json()) as Account[]
        setAccounts(data)
        setSelectedAccountId(data[0]?.id ?? null)

        if (data.length === 0) {
          setIsLoading(false)
          setIsInvestmentsLoading(false)
        }
      } catch {
        setError('Could not load accounts.')
        setInvestmentError('Could not load accounts.')
        setIsLoading(false)
        setIsInvestmentsLoading(false)
      }
    }

    void loadAccounts()
  }, [])

  // REVIEW: Explain why changing selectedAccountId reloads transactions.
  useEffect(() => {
    // REVIEW: Explain why the checked ID is passed into the async function as a number.
    const accountId = selectedAccountId

    if (accountId === null) {
      return
    }

    async function loadTransactions(id: number) {
      try {
        const data = await fetchTransactions(id, dateFrom, dateTo)
        setTransactions(data)
        setCurrentPage(1)
      } catch {
        setError('Could not load transactions.')
      } finally {
        // REVIEW: Explain why loading ends after both success and failure.
        setIsLoading(false)
      }
    }

    void loadTransactions(accountId)
  }, [selectedAccountId, dateFrom, dateTo])

  useEffect(() => {
    const accountId = selectedAccountId

    if (accountId === null) {
      return
    }

    async function loadInvestmentActivities(id: number) {
      try {
        const [activities, summary] = await Promise.all([
          fetchInvestmentActivities(id),
          fetchInvestmentSummary(id),
        ])
        setInvestmentActivities(activities)
        setInvestmentSummary(summary)
        setPriceDrafts(
          Object.fromEntries(
            summary.positions.map((position) => [
              position.ticker,
              position.current_price ?? '',
            ]),
          ),
        )
        setInvestmentPage(1)
      } catch {
        setInvestmentError('Could not load investment activities.')
      } finally {
        setIsInvestmentsLoading(false)
      }
    }

    void loadInvestmentActivities(accountId)
  }, [selectedAccountId])

  // REVIEW: Explain why file uploads use FormData without a manual Content-Type header.
  async function handleIbercajaImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const accountId = selectedAccountId
    const file = selectedFile

    if (accountId === null || file === null) {
      return
    }

    const form = event.currentTarget
    const formData = new FormData()
    formData.append('file', file)

    setIsImporting(true)
    setImportMessage(null)

    try {
      const response = await fetch(
        `/api/accounts/${accountId}/imports/ibercaja`,
        {
          method: 'POST',
          body: formData,
        },
      )

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const result = (await response.json()) as ImportResult
      const refreshedTransactions = await fetchTransactions(
        accountId,
        dateFrom,
        dateTo,
      )

      setTransactions(refreshedTransactions)
      setCurrentPage(1)
      setImportMessage(`Imported ${result.imported} new transactions.`)
      setSelectedFile(null)
      form.reset()
    } catch {
      setImportMessage('The import or transaction refresh failed.')
    } finally {
      setIsImporting(false)
    }
  }

  async function handleRevolutInvestmentImport(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const accountId = selectedAccountId
    const file = selectedInvestmentFile

    if (accountId === null || file === null) {
      return
    }

    const form = event.currentTarget
    const formData = new FormData()
    formData.append('file', file)

    setIsInvestmentImporting(true)
    setInvestmentImportMessage(null)
    setPriceMessage(null)

    try {
      const response = await fetch(
        `/api/accounts/${accountId}/imports/revolut-investments`,
        {
          method: 'POST',
          body: formData,
        },
      )

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const result = (await response.json()) as ImportResult
      const [refreshedActivities, refreshedSummary] = await Promise.all([
        fetchInvestmentActivities(accountId),
        fetchInvestmentSummary(accountId),
      ])

      setInvestmentActivities(refreshedActivities)
      setInvestmentSummary(refreshedSummary)
      setPriceDrafts(
        Object.fromEntries(
          refreshedSummary.positions.map((position) => [
            position.ticker,
            position.current_price ?? '',
          ]),
        ),
      )
      setInvestmentPage(1)
      setInvestmentImportMessage(
        `Imported ${result.imported} new investment activities.`,
      )
      setSelectedInvestmentFile(null)
      form.reset()
    } catch {
      setInvestmentImportMessage(
        'The investment import or activity refresh failed.',
      )
    } finally {
      setIsInvestmentImporting(false)
    }
  }

  async function handleCategoryChange(
    transactionId: number,
    category: string,
  ) {
    setCategoryError(null)

    try {
      const response = await fetch(
        `/api/transactions/${transactionId}/category`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category }),
        },
      )

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const updatedTransaction = (await response.json()) as Transaction

      setTransactions((currentTransactions) =>
        currentTransactions.map((transaction) =>
          transaction.id === updatedTransaction.id
            ? updatedTransaction
            : transaction,
        ),
      )
    } catch {
      setCategoryError('Could not update the transaction category.')
    }
  }

  async function handlePriceUpdate(
    event: FormEvent<HTMLFormElement>,
    ticker: string,
  ) {
    event.preventDefault()

    const accountId = selectedAccountId
    const price = priceDrafts[ticker]?.trim()

    if (accountId === null || !price) {
      return
    }

    setSavingPriceTicker(ticker)
    setPriceMessage(null)

    try {
      const response = await fetch(
        `/api/accounts/${accountId}/investment-prices/${encodeURIComponent(ticker)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ price }),
        },
      )

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const refreshedSummary = await fetchInvestmentSummary(accountId)
      setInvestmentSummary(refreshedSummary)
      setPriceDrafts(
        Object.fromEntries(
          refreshedSummary.positions.map((position) => [
            position.ticker,
            position.current_price ?? '',
          ]),
        ),
      )
      setPriceMessage(`Updated the current price for ${ticker}.`)
    } catch {
      setPriceMessage(`Could not update the current price for ${ticker}.`)
    } finally {
      setSavingPriceTicker(null)
    }
  }

  async function handlePriceRefresh() {
    const accountId = selectedAccountId

    if (accountId === null) {
      return
    }

    setIsRefreshingPrices(true)
    setPriceMessage(null)

    try {
      const response = await fetch(
        `/api/accounts/${accountId}/investment-prices/refresh`,
        { method: 'POST' },
      )

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const result = (await response.json()) as InvestmentPriceRefreshResult
      const refreshedSummary = await fetchInvestmentSummary(accountId)
      setInvestmentSummary(refreshedSummary)
      setPriceDrafts(
        Object.fromEntries(
          refreshedSummary.positions.map((position) => [
            position.ticker,
            position.current_price ?? '',
          ]),
        ),
      )

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

  // REVIEW: Explain the loading, error, and success states before adding more UI.
  let transactionContent: ReactNode

  if (isLoading) {
    transactionContent = <p>Loading transactions...</p>
  } else if (error) {
    transactionContent = <p role="alert">{error}</p>
  } else {
    transactionContent = (
      <section>
        <p>
          {transactions.length === 0
            ? 'No transactions found.'
            : `Showing ${pageStart + 1}–${Math.min(
                pageStart + TRANSACTIONS_PER_PAGE,
                transactions.length,
              )} of ${transactions.length} transactions.`}
        </p>

        <div className="summary">
          <div className="summary-card">
            <span>Money in</span>
            <strong className="amount-positive">
              {euroFormatter.format(moneyIn)}
            </strong>
          </div>

          <div className="summary-card">
            <span>Money out</span>
            <strong className="amount-negative">
              {euroFormatter.format(moneyOut)}
            </strong>
          </div>

          <div className="summary-card">
            <span>Net</span>
            <strong
              className={net >= 0 ? 'amount-positive' : 'amount-negative'}
            >
              {euroFormatter.format(net)}
            </strong>
          </div>
        </div>

        {monthlyTotals.length > 0 && (
          <div className="monthly-chart">
            <h2>Monthly cash flow</h2>

            {monthlyTotals.map((month) => (
              <div className="month-chart" key={month.month}>
                <h3>{month.month}</h3>

                <div className="bar-label">
                  <span>Money in</span>
                  <span>{euroFormatter.format(month.moneyIn)}</span>
                </div>
                <div className="bar-track" aria-hidden="true">
                  <div
                    className="bar bar-in"
                    style={{
                      width: `${(month.moneyIn / largestMonthlyAmount) * 100}%`,
                    }}
                  />
                </div>

                <div className="bar-label">
                  <span>Money out</span>
                  <span>{euroFormatter.format(month.moneyOut)}</span>
                </div>
                <div className="bar-track" aria-hidden="true">
                  <div
                    className="bar bar-out"
                    style={{
                      width: `${(month.moneyOut / largestMonthlyAmount) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {categoryError && <p role="alert">{categoryError}</p>}

        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th>Amount</th>
            </tr>
          </thead>

          <tbody>
            {visibleTransactions.map((transaction) => (
              <tr key={transaction.id}>
                <td>{formatDate(transaction.operation_date)}</td>
                <td>{transaction.description}</td>
                <td>
                  <select
                    value={transaction.category ?? ''}
                    onChange={(event) =>
                      void handleCategoryChange(
                        transaction.id,
                        event.target.value,
                      )
                    }
                  >
                    <option value="" disabled>
                      Uncategorized
                    </option>
                    <option value="housing">Housing</option>
                    <option value="food">Food</option>
                    <option value="transport">Transport</option>
                    <option value="leisure">Leisure</option>
                    <option value="utilities">Utilities</option>
                    <option value="subscriptions">Subscriptions</option>
                    <option value="income">Income</option>
                    <option value="investment">Investment</option>
                    <option value="other">Other</option>
                  </select>
                </td>
                <td
                  className={
                    Number(transaction.amount) >= 0
                      ? 'amount-positive'
                      : 'amount-negative'
                  }
                >
                  {euroFormatter.format(Number(transaction.amount))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {totalPages > 1 && (
          <nav className="pagination" aria-label="Transaction pages">
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

  let investmentContent: ReactNode

  if (isInvestmentsLoading) {
    investmentContent = <p>Loading investment activities...</p>
  } else if (investmentError) {
    investmentContent = <p role="alert">{investmentError}</p>
  } else {
    investmentContent = (
      <section>
        {investmentSummary.currencies.length > 0 && (
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

            {investmentSummary.currencies.map((summary) => (
              <div className="currency-performance" key={summary.currency}>
                <h3>{summary.currency}</h3>

                {summary.priced_positions < summary.total_open_positions && (
                  <p className="missing-prices" role="status">
                    Add prices for all open positions to calculate the complete
                    market value and total result.
                  </p>
                )}

                <div className="summary">
                  <div className="summary-card">
                    <span>Remaining cost</span>
                    <strong>
                      {formatMoney(summary.remaining_cost, summary.currency)}
                    </strong>
                  </div>

                  <div className="summary-card">
                    <span>Market value</span>
                    <strong>
                      {summary.market_value === null
                        ? 'Missing prices'
                        : formatMoney(summary.market_value, summary.currency)}
                    </strong>
                  </div>

                  <div className="summary-card">
                    <span>Unrealized P/L</span>
                    <strong className={amountClass(summary.unrealized_pl)}>
                      {summary.unrealized_pl === null
                        ? '—'
                        : formatMoney(summary.unrealized_pl, summary.currency)}
                    </strong>
                  </div>

                  <div className="summary-card">
                    <span>Realized P/L</span>
                    <strong className={amountClass(summary.realized_pl)}>
                      {formatMoney(summary.realized_pl, summary.currency)}
                    </strong>
                  </div>

                  <div className="summary-card">
                    <span>Dividends</span>
                    <strong className={amountClass(summary.dividends)}>
                      {formatMoney(summary.dividends, summary.currency)}
                    </strong>
                  </div>

                  <div className="summary-card">
                    <span>Total result</span>
                    <strong className={amountClass(summary.total_result)}>
                      {summary.total_result === null
                        ? '—'
                        : formatMoney(summary.total_result, summary.currency)}
                    </strong>
                  </div>
                </div>
              </div>
            ))}

            <h2>Positions</h2>

            {priceMessage && <p role="status">{priceMessage}</p>}

            <div className="positions-grid">
              {investmentSummary.positions.map((position) => (
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

        <h2>Activity history</h2>
        <p>
          {investmentActivities.length === 0
            ? 'No investment activities found.'
            : `Showing ${investmentPageStart + 1}–${Math.min(
                investmentPageStart + INVESTMENT_ACTIVITIES_PER_PAGE,
                investmentActivities.length,
              )} of ${investmentActivities.length} investment activities.`}
        </p>

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
            {visibleInvestmentActivities.map((activity) => (
              <tr key={activity.id}>
                <td>{dateTimeFormatter.format(new Date(activity.occurred_at))}</td>
                <td>{activity.activity_type}</td>
                <td>{activity.ticker ?? '—'}</td>
                <td>{formatQuantity(activity.quantity)}</td>
                <td>
                  {activity.price_per_share === null
                    ? '—'
                    : formatMoney(activity.price_per_share, activity.currency)}
                </td>
                <td>{formatMoney(activity.total_amount, activity.currency)}</td>
                <td>{formatQuantity(activity.fx_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {investmentTotalPages > 1 && (
          <nav className="pagination" aria-label="Investment activity pages">
            <button
              type="button"
              disabled={investmentPage === 1}
              onClick={() => setInvestmentPage((page) => page - 1)}
            >
              Previous
            </button>

            <span>
              Page {investmentPage} of {investmentTotalPages}
            </span>

            <button
              type="button"
              disabled={investmentPage === investmentTotalPages}
              onClick={() => setInvestmentPage((page) => page + 1)}
            >
              Next
            </button>
          </nav>
        )}
      </section>
    )
  }

  return (
    <main>
      <h1>Finanzas</h1>

      <div className="tabs" aria-label="Finance views">
        <button
          type="button"
          className={activeTab === 'transactions' ? 'tab-active' : undefined}
          aria-pressed={activeTab === 'transactions'}
          onClick={() => setActiveTab('transactions')}
        >
          Transactions
        </button>
        <button
          type="button"
          className={activeTab === 'investments' ? 'tab-active' : undefined}
          aria-pressed={activeTab === 'investments'}
          onClick={() => setActiveTab('investments')}
        >
          Investments
        </button>
      </div>

      {accounts.length > 0 && (
        <label>
          Account
          <select
            value={selectedAccountId ?? ''}
            onChange={(event) => {
              setIsLoading(true)
              setIsInvestmentsLoading(true)
              setError(null)
              setInvestmentError(null)
              setSelectedFile(null)
              setSelectedInvestmentFile(null)
              setImportMessage(null)
              setInvestmentImportMessage(null)
              setInvestmentSummary({ positions: [], currencies: [] })
              setPriceDrafts({})
              setPriceMessage(null)
              setSelectedAccountId(Number(event.target.value))
            }}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name} — {account.bank_name}
              </option>
            ))}
          </select>
        </label>
      )}

      {activeTab === 'transactions' && selectedAccountId !== null && (
        <div className="date-filters">
          <label>
            From
            <input
              type="date"
              value={dateFrom}
              max={dateTo || undefined}
              onChange={(event) => {
                setIsLoading(true)
                setError(null)
                setDateFrom(event.target.value)
              }}
            />
          </label>

          <label>
            To
            <input
              type="date"
              value={dateTo}
              min={dateFrom || undefined}
              onChange={(event) => {
                setIsLoading(true)
                setError(null)
                setDateTo(event.target.value)
              }}
            />
          </label>
        </div>
      )}

      {activeTab === 'transactions' && selectedAccountId !== null && (
        <form key={selectedAccountId} onSubmit={handleIbercajaImport}>
          <label htmlFor="ibercaja-file">Ibercaja XLSX</label>

          <input
            id="ibercaja-file"
            type="file"
            accept=".xlsx"
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
        </form>
      )}

      {activeTab === 'transactions' && importMessage && (
        <p role="status">{importMessage}</p>
      )}

      {activeTab === 'investments' && selectedAccountId !== null && (
        <form
          key={`revolut-${selectedAccountId}`}
          onSubmit={handleRevolutInvestmentImport}
        >
          <label htmlFor="revolut-investments-file">
            Revolut investment CSV
          </label>

          <input
            id="revolut-investments-file"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              setSelectedInvestmentFile(event.target.files?.[0] ?? null)
              setInvestmentImportMessage(null)
            }}
          />

          <button
            type="submit"
            disabled={
              selectedInvestmentFile === null || isInvestmentImporting
            }
          >
            {isInvestmentImporting ? 'Importing...' : 'Import'}
          </button>
        </form>
      )}

      {activeTab === 'investments' && investmentImportMessage && (
        <p role="status">{investmentImportMessage}</p>
      )}

      {activeTab === 'transactions' ? transactionContent : investmentContent}
    </main>
  )
}

export default App
