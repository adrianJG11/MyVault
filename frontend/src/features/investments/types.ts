export type InvestmentActivity = {
  id: number
  account_id: number
  occurred_at: string
  ticker: string | null
  activity_type: string
  quantity: string | null
  price_per_share: string | null
  total_amount: string
  currency: string
  fx_rate: string
}

export type InvestmentPosition = {
  ticker: string
  currency: string
  quantity: string
  remaining_cost: string
  current_price: string | null
  market_value: string | null
  unrealized_pl: string | null
  unrealized_return_percent: string | null
  realized_pl: string
  dividends: string
  total_result: string | null
}

export type InvestmentCurrencySummary = {
  currency: string
  remaining_cost: string
  market_value: string | null
  unrealized_pl: string | null
  realized_pl: string
  dividends: string
  total_result: string | null
  priced_positions: number
  total_open_positions: number
}

export type InvestmentSummary = {
  positions: InvestmentPosition[]
  currencies: InvestmentCurrencySummary[]
}

export type InvestmentPriceRefreshResult = {
  updated: string[]
  unavailable: string[]
  manual_only: string[]
}
