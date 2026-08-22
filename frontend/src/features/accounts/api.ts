import type { Account } from './types'

export async function fetchAccounts(): Promise<Account[]> {
  const response = await fetch('/api/accounts')

  if (!response.ok) {
    throw new Error('Could not load accounts')
  }

  return (await response.json()) as Account[]
}
