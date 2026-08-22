const categories = [
  { value: 'housing', label: 'Housing' },
  { value: 'food', label: 'Food' },
  { value: 'transport', label: 'Transport' },
  { value: 'leisure', label: 'Leisure' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'subscriptions', label: 'Subscriptions' },
  { value: 'income', label: 'Income' },
  { value: 'investment', label: 'Investment' },
  { value: 'other', label: 'Other' },
]

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
      {categories.map((categoryOption) => (
        <option key={categoryOption.value} value={categoryOption.value}>
          {categoryOption.label}
        </option>
      ))}
    </select>
  )
}
