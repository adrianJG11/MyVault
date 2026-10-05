import type { Transaction } from './types'

type ImportResult = {
  imported: number
  skipped: number
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

  let response: Response
  try {
    response = await fetch(`/api/accounts/${accountId}/imports/ibercaja`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new Error(
      'Could not confirm the import. Check your connection and reload the page before trying again.',
    )
  }

  if (response.status === 422) {
    throw new Error(
      'This file is not a valid Ibercaja XLSX export. Export it again from Ibercaja and try again.',
    )
  }

  if (response.status === 404) {
    throw new Error(
      'The selected account is no longer available. Reload the page and choose an account.',
    )
  }

  if (response.status === 413) {
    throw new Error('The file is too large. Upload an XLSX export under 10 MB.')
  }

  if (!response.ok) {
    throw new Error(
      'The server could not complete the import. Reload the page before trying again.',
    )
  }

  try {
    return (await response.json()) as ImportResult
  } catch {
    throw new Error(
      'Could not read the import result. Reload the page to check your transactions before trying again.',
    )
  }
}
