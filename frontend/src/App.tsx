import { useEffect, useState } from 'react'

import { fetchAccounts } from './features/accounts/api'
import type { Account } from './features/accounts/types'
import { InvestmentsPanel } from './features/investments/InvestmentsPanel'
import { TransactionsPanel } from './features/transactions/TransactionsPanel'

type ActiveTab = 'transactions' | 'investments'

function App() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<ActiveTab>('transactions')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadAccounts() {
      try {
        const loadedAccounts = await fetchAccounts()
        setAccounts(loadedAccounts)
        setSelectedAccountId(loadedAccounts[0]?.id ?? null)
      } catch {
        setError('Could not load accounts.')
      } finally {
        setIsLoading(false)
      }
    }

    void loadAccounts()
  }, [])

  return (
    <main>
      <header className="page-header">
        <p className="page-eyebrow">Local-first personal finance</p>
        <h1>Dinero</h1>
        <p className="page-description">
          Understand your accounts, spending, and investments.
        </p>
      </header>

      {isLoading && <p>Loading accounts...</p>}
      {error && <p role="alert">{error}</p>}

      {!isLoading && !error && accounts.length === 0 && (
        <p>Create an account through the API before importing data.</p>
      )}

      {accounts.length > 0 && selectedAccountId !== null && (
        <>
          <div className="account-selector">
            <label htmlFor="account">Account</label>

            <select
              id="account"
              value={selectedAccountId}
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

          <div hidden={activeTab !== 'transactions'}>
            <TransactionsPanel
              key={`transactions-${selectedAccountId}`}
              accountId={selectedAccountId}
            />
          </div>
          <div hidden={activeTab !== 'investments'}>
            <InvestmentsPanel
              key={`investments-${selectedAccountId}`}
              accountId={selectedAccountId}
            />
          </div>
        </>
      )}
    </main>
  )
}

export default App
