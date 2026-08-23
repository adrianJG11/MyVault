import { transactionCategories } from './categories'

type TransactionCategorySelectProps = {
  transactionId: number
  category: string | null
  onChange: (transactionId: number, category: string) => Promise<void>
}

export function TransactionCategorySelect({
  transactionId,
  category,
  onChange,
}: TransactionCategorySelectProps) {
  return (
    <select
      value={category ?? ''}
      onChange={(event) => void onChange(transactionId, event.target.value)}
    >
      <option value="" disabled>
        Uncategorized
      </option>
      {transactionCategories.map((categoryOption) => (
        <option key={categoryOption.value} value={categoryOption.value}>
          {categoryOption.label}
        </option>
      ))}
    </select>
  )
}
