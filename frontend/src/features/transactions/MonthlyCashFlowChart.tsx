import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type Props = {
  months: { month: string; moneyIn: number; moneyOut: number }[]
  currency: string
}

function formatMonth(month: string) {
  return new Intl.DateTimeFormat('en-GB', {
    month: 'short',
    year: '2-digit',
  }).format(new Date(`${month}-01T00:00:00`))
}

export default function MonthlyCashFlowChart({ months, currency }: Props) {
  const moneyFormatter = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  })
  const axisFormatter = new Intl.NumberFormat('en-GB', {
    notation: 'compact',
    maximumFractionDigits: 1,
  })

  return (
    <section
      className="chart-card monthly-chart"
      aria-labelledby="cash-flow-heading"
    >
      <div className="chart-heading">
        <div>
          <h2 id="cash-flow-heading">Monthly cash flow</h2>
          <p>Money moving in and out of this account.</p>
        </div>
        <span className="chart-unit">{currency}</span>
      </div>

      <div className="chart-legend" aria-label="Chart legend">
        <span>
          <i className="legend-in" aria-hidden="true" />
          Money in
        </span>
        <span>
          <i className="legend-out" aria-hidden="true" />
          Money out
        </span>
      </div>

      <div
        className="cash-flow-scroll"
        tabIndex={0}
        role="region"
        aria-label="Monthly cash flow chart. Scroll to see more months."
      >
        <div
          className="cash-flow-plot"
          style={{ minWidth: months.length * 48 }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={months}
              margin={{ top: 12, right: 8, left: 0, bottom: 0 }}
              barGap={4}
              maxBarSize={28}
              accessibilityLayer
              title="Monthly money in and money out"
            >
              <CartesianGrid
                vertical={false}
                stroke="var(--border)"
                strokeDasharray="3 5"
              />
              <XAxis
                dataKey="month"
                tickFormatter={formatMonth}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--muted)', fontSize: 11 }}
                tickMargin={12}
                height={40}
              />
              <YAxis
                tickFormatter={(value: number) => axisFormatter.format(value)}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--muted)', fontSize: 11 }}
                width={48}
              />
              <Tooltip
                formatter={(value) => moneyFormatter.format(Number(value))}
                labelFormatter={(value) => formatMonth(String(value))}
                cursor={{ fill: 'var(--surface-raised)' }}
                contentStyle={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                }}
                labelStyle={{ color: 'var(--text)', marginBottom: 6 }}
                isAnimationActive={false}
              />
              <Bar
                dataKey="moneyIn"
                name="Money in"
                fill="var(--money-in)"
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
              <Bar
                dataKey="moneyOut"
                name="Money out"
                fill="var(--money-out)"
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <details className="chart-data">
        <summary>View monthly figures</summary>
        <div className="table-container">
          <table>
            <caption className="sr-only">
              Monthly cash flow in {currency}
            </caption>
            <thead>
              <tr>
                <th scope="col">Month</th>
                <th scope="col">Money in</th>
                <th scope="col">Money out</th>
              </tr>
            </thead>
            <tbody>
              {months.map((month) => (
                <tr key={month.month}>
                  <th scope="row">{formatMonth(month.month)}</th>
                  <td>{moneyFormatter.format(month.moneyIn)}</td>
                  <td>{moneyFormatter.format(month.moneyOut)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  )
}
