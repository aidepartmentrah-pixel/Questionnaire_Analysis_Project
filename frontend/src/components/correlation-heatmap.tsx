import type { CorrelationMatrix } from '@/lib/api'

interface CorrelationHeatmapProps {
  correlation: CorrelationMatrix
}

// A discrete 5-step sequential ramp rather than a continuous alpha blend:
// each step's background/text pairing is pre-verified to clear WCAG AA's
// 4.5:1 text contrast (a continuous blend from a pale to a saturated blue
// has an unavoidable "dead zone" in the middle where neither white nor
// dark text reaches 4.5:1 against the background, since luminance crosses
// the crossover point gradually rather than in one jump).
const INTENSITY_STEPS: { max: number; background: string; color: string }[] = [
  { max: 0.2, background: '#eff6ff', color: '#111827' },
  { max: 0.4, background: '#bfdbfe', color: '#111827' },
  { max: 0.6, background: '#60a5fa', color: '#111827' },
  { max: 0.8, background: '#2563eb', color: '#ffffff' },
  { max: Infinity, background: '#1e3a8a', color: '#ffffff' },
]

function cellStyle(value: number | null): { backgroundColor: string; color: string } | undefined {
  if (value === null) return undefined
  const magnitude = Math.min(1, Math.abs(value))
  const step = INTENSITY_STEPS.find((s) => magnitude <= s.max) ?? INTENSITY_STEPS[INTENSITY_STEPS.length - 1]
  return { backgroundColor: step.background, color: step.color }
}

export function CorrelationHeatmap({ correlation }: CorrelationHeatmapProps) {
  const { columns, matrix } = correlation

  return (
    <div
      className="overflow-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      tabIndex={0}
      role="region"
      aria-label="Correlation heatmap"
    >
      <table className="border-collapse text-xs">
        <thead>
          <tr>
            <th className="p-1" />
            {columns.map((column) => (
              <th
                key={column}
                scope="col"
                className="whitespace-nowrap p-1 font-medium text-muted-foreground"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {columns.map((rowLabel, rowIndex) => (
            <tr key={rowLabel}>
              <th
                scope="row"
                className="whitespace-nowrap p-1 text-right font-medium text-muted-foreground"
              >
                {rowLabel}
              </th>
              {matrix[rowIndex]?.map((value, colIndex) => (
                <td
                  key={columns[colIndex]}
                  className="h-8 w-14 border border-border text-center"
                  style={cellStyle(value)}
                >
                  {value === null ? '—' : value.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
