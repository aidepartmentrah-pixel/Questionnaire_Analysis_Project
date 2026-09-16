import type { ConfusionMatrix } from '@/lib/api'

interface ConfusionMatrixViewProps {
  confusion: ConfusionMatrix
}

export function ConfusionMatrixView({ confusion }: ConfusionMatrixViewProps) {
  const { labels, matrix } = confusion
  const maxValue = Math.max(1, ...matrix.flat())
  const support = matrix.map((row) => row.reduce((sum, v) => sum + v, 0))

  return (
    <div>
      <div
        className="overflow-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        tabIndex={0}
        role="region"
        aria-label="Confusion matrix"
      >
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-1" />
              <th
                colSpan={labels.length}
                scope="colgroup"
                className="p-1 text-center font-medium text-muted-foreground"
              >
                Predicted
              </th>
            </tr>
            <tr>
              <th className="p-1" />
              {labels.map((label) => (
                <th
                  key={label}
                  scope="col"
                  className="whitespace-nowrap p-1 font-medium text-muted-foreground"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((rowLabel, rowIndex) => (
              <tr key={rowLabel}>
                <th
                  scope="row"
                  className="whitespace-nowrap p-1 text-right font-medium text-muted-foreground"
                >
                  {rowLabel}
                </th>
                {matrix[rowIndex]?.map((value, colIndex) => {
                  const isDiagonal = rowIndex === colIndex
                  const intensity = value === 0 ? 0 : Math.min(1, value / maxValue + 0.15)
                  return (
                    <td
                      key={labels[colIndex]}
                      className="h-10 w-14 border border-border text-center font-medium"
                      style={{
                        backgroundColor: isDiagonal
                          ? `rgba(34, 197, 94, ${intensity})`
                          : `rgba(239, 68, 68, ${intensity})`,
                        color: intensity > 0.55 ? '#fff' : undefined,
                      }}
                    >
                      {value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Rows are actual classes, columns are predicted classes; diagonal cells are correct
        predictions.
      </p>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {labels.map((label, index) => (
          <span key={label}>
            Class {label}: {support[index]} in test set
          </span>
        ))}
      </div>
    </div>
  )
}
