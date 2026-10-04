import { lazy, Suspense, type SubmitEvent, useEffect, useState } from 'react'

import { TransactionCategorySelect } from './TransactionCategorySelect'
import {
  fetchTransactions,
  importIbercajaTransactions,
  updateTransactionCategory,
} from './api'
import type { Transaction } from './types'
import { transactionCategories } from './categories'

const TRANSACTIONS_PER_PAGE = 10
const MonthlyCashFlowChart = lazy(() => import('./MonthlyCashFlowChart'))

function formatDate(value: string) {
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

function formatCategory(category: string) {
  return category.charAt(0).toUpperCase() + category.slice(1)
}

type TransactionsPanelProps = {
  accountId: number
  currency: string
  onImportComplete: () => Promise<void>
}

export function TransactionsPanel({
  accountId,
  currency,
  onImportComplete,
}: TransactionsPanelProps) {
  const moneyFormatter = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  })
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [error, setError] = useState<string | null>(null)
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importMessage, setImportMessage] = useState<{
    text: string
    tone: 'success' | 'error'
  } | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [monthFilter, setMonthFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [descriptionFilter, setDescriptionFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const hasActiveFilters =
    dateFrom !== '' ||
    dateTo !== '' ||
    categoryFilter !== '' ||
    descriptionFilter !== ''

  const totalPages = Math.max(
    1,
    Math.ceil(transactions.length / TRANSACTIONS_PER_PAGE),
  )
  const pageStart = (currentPage - 1) * TRANSACTIONS_PER_PAGE
  const visibleTransactions = transactions.slice(
    pageStart,
    pageStart + TRANSACTIONS_PER_PAGE,
  )

  const moneyIn = transactions
    .filter((transaction) => Number(transaction.amount) > 0)
    .reduce((total, transaction) => total + Number(transaction.amount), 0)

  const moneyOut = transactions
    .filter((transaction) => Number(transaction.amount) < 0)
    .reduce(
      (total, transaction) => total + Math.abs(Number(transaction.amount)),
      0,
    )

  const net = moneyIn - moneyOut

  const spendingByCategory = new Map<string, number>()

  for (const transaction of transactions) {
    const amount = Number(transaction.amount)

    if (
      transaction.category === 'investment' ||
      transaction.category === 'income' ||
      (amount >= 0 && transaction.category === null)
    ) {
      continue
    }

    const category = transaction.category ?? 'uncategorized'
    spendingByCategory.set(
      category,
      (spendingByCategory.get(category) ?? 0) - amount,
    )
  }

  const categorySpending = [...spendingByCategory.entries()]
    .map(([category, amount]) => ({ category, amount }))
    .filter((category) => category.amount > 0)
    .sort((first, second) => second.amount - first.amount)

  const largestCategoryAmount = Math.max(
    1,
    ...categorySpending.map((category) => category.amount),
  )

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
    .map(([month, totals]) => ({ month, ...totals }))
    .sort((first, second) => first.month.localeCompare(second.month))

  useEffect(() => {
    async function loadTransactions() {
      try {
        const data = await fetchTransactions(
          accountId,
          dateFrom,
          dateTo,
          categoryFilter,
          descriptionFilter,
        )
        setTransactions(data)
        setCurrentPage(1)
      } catch {
        setError('Could not load transactions.')
      } finally {
        setIsLoading(false)
      }
    }

    void loadTransactions()
  }, [accountId, dateFrom, dateTo, categoryFilter, descriptionFilter])

  async function handleIbercajaImport(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()

    if (selectedFile === null) {
      return
    }

    const form = event.currentTarget
    const file = selectedFile
    setIsImporting(true)
    setImportMessage(null)

    try {
      const result = await importIbercajaTransactions(accountId, file)
      const refreshedTransactions = await fetchTransactions(
        accountId,
        dateFrom,
        dateTo,
        categoryFilter,
        descriptionFilter,
      )
      await onImportComplete()

      setTransactions(refreshedTransactions)
      setCurrentPage(1)
      setImportMessage({
        text: `Imported ${result.imported} new transactions.`,
        tone: 'success',
      })
      setSelectedFile(null)
      form.reset()
    } catch {
      setImportMessage({
        text: 'The import or transaction refresh failed.',
        tone: 'error',
      })
    } finally {
      setIsImporting(false)
    }
  }

  async function handleCategoryChange(transactionId: number, category: string) {
    setCategoryError(null)

    try {
      await updateTransactionCategory(transactionId, category)

      const refreshedTransactions = await fetchTransactions(
        accountId,
        dateFrom,
        dateTo,
        categoryFilter,
        descriptionFilter,
      )

      setTransactions(refreshedTransactions)
      setCurrentPage(1)
    } catch {
      setCategoryError('Could not update the transaction category.')
    }
  }

  function handleMonthChange(month: string) {
    setMonthFilter(month)
    setIsLoading(true)
    setError(null)

    if (month === '') {
      setDateFrom('')
      setDateTo('')
      return
    }

    const [year, monthNumber] = month.split('-').map(Number)
    const lastDay = new Date(year, monthNumber, 0).getDate()

    setDateFrom(`${month}-01`)
    setDateTo(`${month}-${String(lastDay).padStart(2, '0')}`)
  }

  function handleClearFilters() {
    setIsLoading(true)
    setError(null)
    setMonthFilter('')
    setDateFrom('')
    setDateTo('')
    setCategoryFilter('')
    setDescriptionFilter('')
  }

  let content

  if (isLoading) {
    content = <p className="notice notice-info">Loading transactions...</p>
  } else if (error) {
    content = (
      <p className="notice notice-error" role="alert">
        {error}
      </p>
    )
  } else {
    content = (
      <section
        className="transaction-overview"
        aria-label="Transaction overview"
      >
        <div className="overview-heading">
          <h2>Your account at a glance</h2>
          <p>
            {hasActiveFilters
              ? 'Based on the matching transactions below.'
              : 'Based on all imported transactions in this account.'}
          </p>
        </div>
        <div className="summary transaction-summary">
          <div className="summary-card">
            <span>Money in</span>
            <strong className="amount-positive">
              {moneyFormatter.format(moneyIn)}
            </strong>
            <small>Incoming payments</small>
          </div>

          <div className="summary-card">
            <span>Money out</span>
            <strong className="amount-negative">
              {moneyFormatter.format(moneyOut)}
            </strong>
            <small>Outgoing payments</small>
          </div>

          <div className="summary-card summary-card-highlight">
            <span>Net cash flow</span>
            <strong
              className={net >= 0 ? 'amount-positive' : 'amount-negative'}
            >
              {moneyFormatter.format(net)}
            </strong>
            <small>Money in minus money out</small>
          </div>
        </div>

        {transactions.length > 0 && (
          <div className="transaction-charts">
            <Suspense
              fallback={
                <p className="chart-card" role="status">
                  Loading cash flow chart…
                </p>
              }
            >
              <MonthlyCashFlowChart
                months={monthlyTotals}
                currency={currency}
              />
            </Suspense>
            <section
              className="chart-card category-chart"
              aria-labelledby="category-heading"
            >
              <div className="chart-heading">
                <div>
                  <h2 id="category-heading">Spending by category</h2>
                  <p>
                    Net spending after refunds. Excludes income and investments.
                  </p>
                </div>
              </div>
              {categorySpending.length === 0 && (
                <p className="chart-empty">
                  No category spending in this selection.
                </p>
              )}

              <div className="category-bars">
                {categorySpending.map((category) => (
                  <div key={category.category}>
                    <div className="bar-label">
                      <span>{formatCategory(category.category)}</span>
                      <span>{moneyFormatter.format(category.amount)}</span>
                    </div>
                    <div className="bar-track" aria-hidden="true">
                      <div
                        className="bar bar-category"
                        style={{
                          width: `${(category.amount / largestCategoryAmount) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {categoryError && (
          <p className="notice notice-error" role="alert">
            {categoryError}
          </p>
        )}

        <div className="table-header">
          <h2>Transactions</h2>

          <p>
            {transactions.length === 0
              ? 'No transactions found.'
              : `Showing ${pageStart + 1}–${Math.min(
                  pageStart + TRANSACTIONS_PER_PAGE,
                  transactions.length,
                )} of ${transactions.length} transactions.`}
          </p>
        </div>

        {transactions.length === 0 ? (
          <div className="empty-state">
            <h3>
              {hasActiveFilters
                ? 'No matching transactions'
                : 'Your transactions will appear here'}
            </h3>
            <p>
              {hasActiveFilters
                ? 'Try a different period or clear the filters.'
                : 'Import an Ibercaja XLSX export to see your cash flow and spending.'}
            </p>
          </div>
        ) : (
          <div
            className="table-container transaction-table"
            tabIndex={0}
            role="region"
            aria-label="Transactions table"
          >
            <table>
              <caption className="sr-only">Transactions in {currency}</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Description</th>
                  <th scope="col">Category</th>
                  <th scope="col">Amount</th>
                </tr>
              </thead>

              <tbody>
                {visibleTransactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td>{formatDate(transaction.operation_date)}</td>
                    <td className="transaction-description">
                      {transaction.description}
                    </td>
                    <td>
                      <TransactionCategorySelect
                        transactionId={transaction.id}
                        category={transaction.category}
                        onChange={handleCategoryChange}
                      />
                    </td>
                    <td
                      className={
                        Number(transaction.amount) >= 0
                          ? 'amount-positive'
                          : 'amount-negative'
                      }
                    >
                      {moneyFormatter.format(Number(transaction.amount))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

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

  return (
    <>
      <section className="filter-panel" aria-labelledby="filters-heading">
        <div className="filter-heading">
          <h2 id="filters-heading">Explore your transactions</h2>
          <button
            type="button"
            disabled={!hasActiveFilters}
            onClick={handleClearFilters}
          >
            Clear filters
          </button>
        </div>

        <div className="date-filters">
          <label>
            Month
            <input
              type="month"
              value={monthFilter}
              onChange={(event) => handleMonthChange(event.target.value)}
            />
          </label>

          <label>
            From
            <input
              type="date"
              value={dateFrom}
              max={dateTo || undefined}
              onChange={(event) => {
                setIsLoading(true)
                setError(null)
                setMonthFilter('')
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
                setMonthFilter('')
                setDateTo(event.target.value)
              }}
            />
          </label>

          <label>
            Category
            <select
              value={categoryFilter}
              onChange={(event) => {
                setIsLoading(true)
                setError(null)
                setCategoryFilter(event.target.value)
              }}
            >
              <option value="">All categories</option>
              <option value="uncategorized">Uncategorized</option>

              {transactionCategories.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Search
            <input
              type="search"
              value={descriptionFilter}
              placeholder="Transaction description"
              onChange={(event) => {
                setIsLoading(true)
                setError(null)
                setDescriptionFilter(event.target.value)
              }}
            />
          </label>
        </div>
      </section>

      <details className="import-panel">
        <summary>Import transactions</summary>

        <form onSubmit={handleIbercajaImport}>
          <p>Upload an Ibercaja XLSX export for the selected account.</p>

          <div className="import-controls">
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
          </div>
        </form>
      </details>

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
