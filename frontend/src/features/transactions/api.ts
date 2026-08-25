import type { Transaction } from './types'

type ImportResult = {
  imported: number
}

export async function fetchTransactions(
  accountId: number,
  dateFrom: string,
  dateTo: string,
  category: string,
  description: string,
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

  if (category) {
    params.set('category', category)
  }

  if (description.trim()) {
    params.set('description', description.trim())
  }

  const response = await fetch(`/api/transactions?${params}`)

  if (!response.ok) {
    throw new Error('Could not load transactions')
  }

  return (await response.json()) as Transaction[]
}

export async function updateTransactionCategory(
  transactionId: number,
  category: string,
): Promise<Transaction> {
  const response = await fetch(
    `/api/transactions/${transactionId}/category`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category }),
    },
  )

  if (!response.ok) {
    throw new Error('Could not update transaction category')
  }

  return (await response.json()) as Transaction
}

export async function importIbercajaTransactions(
  accountId: number,
  file: File,
): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`/api/accounts/${accountId}/imports/ibercaja`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Could not import Ibercaja transactions')
  }

  return (await response.json()) as ImportResult
}
