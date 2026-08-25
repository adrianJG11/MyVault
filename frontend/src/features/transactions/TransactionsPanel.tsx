import { type SubmitEvent, useEffect, useState } from 'react'

import { TransactionCategorySelect } from './TransactionCategorySelect'
import {
  fetchTransactions,
  importIbercajaTransactions,
  updateTransactionCategory,
} from './api'
import type { Transaction } from './types'
import { transactionCategories } from './categories'

const TRANSACTIONS_PER_PAGE = 10

const euroFormatter = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
})

function formatDate(value: string) {
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

function formatCategory(category: string) {
  return category.charAt(0).toUpperCase() + category.slice(1)
}

type TransactionsPanelProps = {
  accountId: number
}

export function TransactionsPanel({ accountId }: TransactionsPanelProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [error, setError] = useState<string | null>(null)
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

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

  const largestMonthlyAmount = Math.max(
    1,
    ...monthlyTotals.flatMap((month) => [month.moneyIn, month.moneyOut]),
  )

  useEffect(() => {
    async function loadTransactions() {
      try {
        const data = await fetchTransactions(
          accountId,
          dateFrom,
          dateTo,
          categoryFilter,
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
  }, [accountId, dateFrom, dateTo, categoryFilter])

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

  async function handleCategoryChange(
    transactionId: number,
    category: string,
  ) {
    setCategoryError(null)

    try {
      await updateTransactionCategory(transactionId, category)

      const refreshedTransactions = await fetchTransactions(
        accountId,
        dateFrom,
        dateTo,
        categoryFilter,
      )

      setTransactions(refreshedTransactions)
      setCurrentPage(1)
    } catch {
      setCategoryError('Could not update the transaction category.')
    }
  }

  let content

  if (isLoading) {
    content = <p>Loading transactions...</p>
  } else if (error) {
    content = <p role="alert">{error}</p>
  } else {
    content = (
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

        {categorySpending.length > 0 && (
          <div className="category-chart">
            <h2>Net spending by category</h2>

            {categorySpending.map((category) => (
              <div key={category.category}>
                <div className="bar-label">
                  <span>{formatCategory(category.category)}</span>
                  <span>{euroFormatter.format(category.amount)}</span>
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
        )}

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

  return (
    <>
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

      {transactionCategories.map((category) => (
        <option key={category.value} value={category.value}>
          {category.label}
        </option>
      ))}
    </select>
  </label>
      </div>

      <form onSubmit={handleIbercajaImport}>
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
        <button type="submit" disabled={selectedFile === null || isImporting}>
          {isImporting ? 'Importing...' : 'Import'}
        </button>
      </form>

      {importMessage && <p role="status">{importMessage}</p>}
      {content}
    </>
  )
}
