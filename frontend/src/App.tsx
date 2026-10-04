import { useEffect, useState } from 'react'

import { fetchAccounts } from './features/accounts/api'
import { AccountCreateForm } from './features/accounts/AccountCreateForm'
import type { Account } from './features/accounts/types'
import { InvestmentsPanel } from './features/investments/InvestmentsPanel'
import { TransactionsPanel } from './features/transactions/TransactionsPanel'

type ActiveTab = 'transactions' | 'investments'

function formatMoney(value: string, currency: string) {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  }).format(Number(value))
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
  }).format(new Date(`${value}T00:00:00`))
}

function App() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(
    null,
  )
  const [activeTab, setActiveTab] = useState<ActiveTab>('transactions')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const selectedAccount =
    accounts.find((account) => account.id === selectedAccountId) ?? null

  async function refreshAccounts() {
    const refreshedAccounts = await fetchAccounts()
    setAccounts(refreshedAccounts)
  }

  function handleAccountCreated(account: Account) {
    setAccounts((currentAccounts) => [...currentAccounts, account])
    setSelectedAccountId(account.id)
  }

  useEffect(() => {
    async function loadAccounts() {
      try {
        const loadedAccounts = await fetchAccounts()
        setAccounts(loadedAccounts)
        setSelectedAccountId(loadedAccounts[0]?.id ?? null)
      } catch {
        setError('Could not load accounts. Reload the page to try again.')
      } finally {
        setIsLoading(false)
      }
    }

    void loadAccounts()
  }, [])

  return (
    <main>
      <header className="page-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            MV
          </span>
          <div>
            <h1>MyVault</h1>
            <p className="page-description">Your money, in perspective.</p>
          </div>
        </div>
      </header>

      {isLoading && (
        <p className="notice notice-info" role="status">
          Loading accounts…
        </p>
      )}
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}

      {!isLoading && !error && (
        <details
          className="import-panel account-create-panel"
          open={accounts.length === 0}
        >
          <summary>Add account</summary>
          {accounts.length === 0 && (
            <p className="notice notice-info">
              Create your first account to start importing transactions.
            </p>
          )}
          <AccountCreateForm onCreated={handleAccountCreated} />
        </details>
      )}

      {selectedAccount !== null && (
        <>
          <div className="app-toolbar">
            <div className="account-selector">
              <label htmlFor="account">Selected account</label>

              <select
                id="account"
                value={selectedAccount.id}
                onChange={(event) =>
                  setSelectedAccountId(Number(event.target.value))
                }
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} — {account.bank_name}
                  </option>
                ))}
              </select>

              <div className="account-balance">
                <span>Last known balance</span>
                <strong>
                  {selectedAccount.current_balance === null
                    ? 'Balance unavailable'
                    : formatMoney(
                        selectedAccount.current_balance,
                        selectedAccount.currency,
                      )}
                </strong>
                {selectedAccount.balance_date !== null && (
                  <small>
                    As of {formatDate(selectedAccount.balance_date)}
                  </small>
                )}
              </div>
            </div>

            <nav className="tabs" aria-label="Finance sections">
              <button
                type="button"
                className={activeTab === 'transactions' ? 'active' : undefined}
                aria-current={activeTab === 'transactions' ? 'page' : undefined}
                onClick={() => setActiveTab('transactions')}
              >
                Transactions
              </button>
              <button
                type="button"
                className={activeTab === 'investments' ? 'active' : undefined}
                aria-current={activeTab === 'investments' ? 'page' : undefined}
                onClick={() => setActiveTab('investments')}
              >
                Investments
              </button>
            </nav>
          </div>

          <div hidden={activeTab !== 'transactions'}>
            <TransactionsPanel
              key={`transactions-${selectedAccount.id}`}
              accountId={selectedAccount.id}
              currency={selectedAccount.currency}
              onImportComplete={refreshAccounts}
            />
          </div>
          <div hidden={activeTab !== 'investments'}>
            <InvestmentsPanel
              key={`investments-${selectedAccount.id}`}
              accountId={selectedAccount.id}
            />
          </div>
        </>
      )}
    </main>
  )
}

export default App
