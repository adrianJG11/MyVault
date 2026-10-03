import type {
  InvestmentActivity,
  InvestmentPriceRefreshResult,
  InvestmentSummary,
} from './types'

type ImportResult = {
  imported: number
  prices_updated?: number
}

export async function fetchInvestmentActivities(
  accountId: number,
): Promise<InvestmentActivity[]> {
  const response = await fetch(
    `/api/investment-activities?account_id=${accountId}`,
  )

  if (!response.ok) {
    throw new Error('Could not load investment activities')
  }

  return (await response.json()) as InvestmentActivity[]
}

export async function fetchInvestmentSummary(
  accountId: number,
): Promise<InvestmentSummary> {
  const response = await fetch(`/api/investment-summary?account_id=${accountId}`)

  if (!response.ok) {
    throw new Error('Could not load investment summary')
  }

  return (await response.json()) as InvestmentSummary
}

export async function importInvestments(
  accountId: number,
  file: File,
  broker: 'revolut' | 'ibkr',
): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(
    `/api/accounts/${accountId}/imports/${broker}-investments`,
    {
      method: 'POST',
      body: formData,
    },
  )

  if (!response.ok) {
    throw new Error(`Could not import ${broker} investments`)
  }

  return (await response.json()) as ImportResult
}

export async function updateInvestmentPrice(
  accountId: number,
  ticker: string,
  price: string,
): Promise<void> {
  const response = await fetch(
    `/api/accounts/${accountId}/investment-prices/${encodeURIComponent(ticker)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price }),
    },
  )

  if (!response.ok) {
    throw new Error('Could not update investment price')
  }
}

export async function refreshInvestmentPrices(
  accountId: number,
): Promise<InvestmentPriceRefreshResult> {
  const response = await fetch(
    `/api/accounts/${accountId}/investment-prices/refresh`,
    { method: 'POST' },
  )

  if (!response.ok) {
    throw new Error('Could not refresh investment prices')
  }

  return (await response.json()) as InvestmentPriceRefreshResult
}
