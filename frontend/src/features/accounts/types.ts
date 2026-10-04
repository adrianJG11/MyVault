export type Account = {
  id: number
  name: string
  bank_name: string
  currency: string
  current_balance: string | null
  balance_date: string | null
}

export type AccountCreate = {
  name: string
  bank_name: string
  currency: string
}
