import {
  Bar,
  BarChart,
  CartesianGrid,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { InvestmentPosition } from './types'

const ALLOCATION_COLORS = [
  'var(--accent)',
  'var(--money-in)',
  'var(--money-out)',
  '#c6b4df',
  '#8ccbd7',
  '#d5c58e',
]

type Props = {
  positions: InvestmentPosition[]
  currency: string
  marketValue: string | null
}

export default function InvestmentCharts({
  positions,
  currency,
  marketValue,
}: Props) {
  const openPositions = positions.filter(
    (position) =>
      position.currency === currency && Number(position.quantity) > 0,
  )
  const allocation = openPositions
    .filter(
      (position) =>
        position.market_value !== null && Number(position.market_value) > 0,
    )
    .sort(
      (first, second) =>
        Number(second.market_value) - Number(first.market_value),
    )
    .map((position, index) => ({
      ticker: position.ticker,
      value: Number(position.market_value),
      fill: ALLOCATION_COLORS[index % ALLOCATION_COLORS.length],
    }))
  const results = openPositions
    .filter((position) => position.unrealized_pl !== null)
    .map((position) => ({
      ticker: position.ticker,
      result: Number(position.unrealized_pl),
      fill:
        Number(position.unrealized_pl) >= 0
          ? 'var(--money-in)'
          : 'var(--money-out)',
    }))
    .sort((first, second) => second.result - first.result)
  const moneyFormatter = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  })
  const percentFormatter = new Intl.NumberFormat('en-GB', {
    style: 'percent',
    maximumFractionDigits: 1,
  })
  const axisFormatter = new Intl.NumberFormat('en-GB', {
    notation: 'compact',
    maximumFractionDigits: 1,
  })
  const tooltipStyle = {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 8,
  }

  return (
    <div className="investment-charts">
      <section
        className="chart-card"
        aria-label={`Portfolio allocation in ${currency}`}
      >
        <div className="chart-heading">
          <div>
            <h3>Portfolio allocation</h3>
            <p>Open positions by market value.</p>
          </div>
          <span className="chart-unit">{currency}</span>
        </div>
        {marketValue !== null &&
        Number(marketValue) > 0 &&
        allocation.length > 0 ? (
          <div className="portfolio-allocation">
            <div className="allocation-donut">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart
                  accessibilityLayer
                  title={`Portfolio allocation in ${currency}`}
                >
                  <Pie
                    data={allocation}
                    dataKey="value"
                    nameKey="ticker"
                    innerRadius={60}
                    outerRadius={88}
                    paddingAngle={3}
                    stroke="var(--surface)"
                    isAnimationActive={false}
                  />
                  <Tooltip
                    formatter={(value) => moneyFormatter.format(Number(value))}
                    contentStyle={tooltipStyle}
                    itemStyle={{ color: 'var(--text)' }}
                    isAnimationActive={false}
                  />
                </PieChart>
              </ResponsiveContainer>
              <span className="donut-center" aria-hidden="true">
                <strong>{allocation.length}</strong>
                <small>holdings</small>
              </span>
            </div>
            <ul className="allocation-list">
              {allocation.map((position) => (
                <li key={position.ticker}>
                  <span className="allocation-name">
                    <i
                      style={{ background: position.fill }}
                      aria-hidden="true"
                    />
                    {position.ticker}
                  </span>
                  <span className="allocation-value">
                    <strong>
                      {percentFormatter.format(
                        position.value / Number(marketValue),
                      )}
                    </strong>
                    <small>{moneyFormatter.format(position.value)}</small>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="chart-empty">
            {openPositions.length === 0
              ? 'No open positions to allocate.'
              : marketValue === null
                ? 'Add the missing prices to see the complete allocation.'
                : 'Open positions have no market value to allocate.'}
          </p>
        )}
      </section>

      <section
        className="chart-card"
        aria-label={`Unrealized profit and loss in ${currency}`}
      >
        <div className="chart-heading">
          <div>
            <h3>Unrealized profit / loss</h3>
            <p>Open positions with a saved price. Excludes dividends.</p>
          </div>
          <span className="chart-unit">{currency}</span>
        </div>
        {results.length > 0 ? (
          <>
            <div
              className="returns-scroll"
              tabIndex={0}
              role="region"
              aria-label={`Profit and loss chart in ${currency}`}
            >
              <div style={{ height: Math.max(210, results.length * 44) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={results}
                    layout="vertical"
                    margin={{ top: 16, right: 16, left: 0, bottom: 0 }}
                    maxBarSize={18}
                    accessibilityLayer
                    title={`Unrealized profit and loss in ${currency}`}
                  >
                    <CartesianGrid
                      horizontal={false}
                      stroke="var(--border)"
                      strokeDasharray="3 5"
                    />
                    <XAxis
                      type="number"
                      tickFormatter={(value: number) =>
                        axisFormatter.format(value)
                      }
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: 'var(--muted)', fontSize: 11 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="ticker"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: 'var(--text)', fontSize: 11 }}
                      width={65}
                    />
                    <ReferenceLine x={0} stroke="var(--muted)" />
                    <Tooltip
                      formatter={(value) =>
                        moneyFormatter.format(Number(value))
                      }
                      contentStyle={tooltipStyle}
                      labelStyle={{ color: 'var(--text)' }}
                      itemStyle={{ color: 'var(--text)' }}
                      cursor={{ fill: 'var(--surface-raised)' }}
                      isAnimationActive={false}
                    />
                    <Bar
                      dataKey="result"
                      name="Unrealized P/L"
                      radius={[3, 3, 3, 3]}
                      isAnimationActive={false}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <details className="chart-data">
              <summary>View position results</summary>
              <div className="table-container">
                <table>
                  <caption className="sr-only">
                    Unrealized results in {currency}
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Holding</th>
                      <th scope="col">Unrealized P/L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((position) => (
                      <tr key={position.ticker}>
                        <th scope="row">{position.ticker}</th>
                        <td>{moneyFormatter.format(position.result)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        ) : (
          <p className="chart-empty">
            {openPositions.length === 0
              ? 'No open positions to compare.'
              : 'Add saved prices to see unrealized results.'}
          </p>
        )}
      </section>
    </div>
  )
}
