import type { ColumnInfo } from '@/lib/api'
import { Badge } from '@/components/ui/badge'

interface DatasetPreviewTableProps {
  columns: ColumnInfo[]
  rows: Record<string, unknown>[]
}

export function DatasetPreviewTable({ columns, rows }: DatasetPreviewTableProps) {
  return (
    <div
      className="max-h-90 overflow-auto rounded-md border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      tabIndex={0}
      role="region"
      aria-label="Dataset preview table"
    >
      <table className="w-full min-w-max border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-muted">
          <tr>
            {columns.map((column) => (
              <th
                key={column.name}
                scope="col"
                className="whitespace-nowrap border-b border-border px-3 py-2 text-left font-medium"
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-foreground">{column.name}</span>
                  <Badge variant="outline" className="font-normal text-[10px]">
                    {column.dtype}
                  </Badge>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-border last:border-0 even:bg-muted/30">
              {columns.map((column) => {
                const value = row[column.name]
                return (
                  <td key={column.name} className="whitespace-nowrap px-3 py-1.5 text-foreground">
                    {value === null || value === undefined ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      String(value)
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
