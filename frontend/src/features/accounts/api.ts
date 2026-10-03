import type { Account, AccountCreate } from './types'

export async function fetchAccounts(): Promise<Account[]> {
  const response = await fetch('/api/accounts')

  if (!response.ok) {
    throw new Error('Could not load accounts')
  }

  return (await response.json()) as Account[]
}

export async function createAccount(
  account: AccountCreate,
): Promise<Account> {
  const response = await fetch('/api/accounts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(account),
  })

  if (!response.ok) {
    throw new Error('Could not create account')
  }

  return (await response.json()) as Account
}
