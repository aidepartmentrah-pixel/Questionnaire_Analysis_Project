interface BarListItem {
  label: string
  count: number
}

interface BarListProps {
  items: BarListItem[]
}

export function BarList({ items }: BarListProps) {
  const maxCount = Math.max(1, ...items.map((item) => item.count))

  return (
    <div className="space-y-1.5">
      {items.map((item, index) => (
        <div key={`${item.label}-${index}`} className="flex items-center gap-2">
          <span className="w-32 shrink-0 truncate text-xs text-muted-foreground" title={item.label}>
            {item.label}
          </span>
          <div className="h-3.5 flex-1 overflow-hidden rounded bg-secondary">
            <div
              className="h-full rounded bg-primary"
              style={{ width: `${(item.count / maxCount) * 100}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right text-xs text-muted-foreground">
            {item.count}
          </span>
        </div>
      ))}
    </div>
  )
}
