// Dates and Decimal amounts arrive as strings because JSON has no date or Decimal type.
export type Transaction = {
  id: number
  account_id: number
  operation_date: string
  value_date: string
  amount: string
  balance_after: string
  bank_concept: string
  description: string
  category: string | null
}
