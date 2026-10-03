import { type SubmitEvent, useState } from 'react'

import { createAccount } from './api'
import type { Account } from './types'

type Props = {
  onCreated: (account: Account) => void
}

export function AccountCreateForm({ onCreated }: Props) {
  const [name, setName] = useState('')
  const [bankName, setBankName] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    setError(null)
    if (!name.trim() || !bankName.trim()) {
      setError('Enter an account name and a bank or broker name.')
      return
    }

    setIsSubmitting(true)
    try {
      const account = await createAccount({
        name: name.trim(),
        bank_name: bankName.trim(),
        currency,
      })
      onCreated(account)
      setName('')
      setBankName('')
    } catch {
      setError('Could not create account. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="account-fields">
        <label htmlFor="account-name">
          Account name
          <input
            id="account-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={100}
            disabled={isSubmitting}
          />
        </label>
        <label htmlFor="account-bank">
          Bank or broker
          <input
            id="account-bank"
            value={bankName}
            onChange={(event) => setBankName(event.target.value)}
            required
            maxLength={100}
            disabled={isSubmitting}
          />
        </label>
        <label htmlFor="account-currency">
          Currency
          <select
            id="account-currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            disabled={isSubmitting}
          >
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
          </select>
        </label>
      </div>
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      <div className="import-controls">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account...' : 'Create account'}
        </button>
      </div>
    </form>
  )
}
