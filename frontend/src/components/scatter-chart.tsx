interface ScatterPoint {
  x: number
  y: number
}

interface ScatterChartProps {
  points: ScatterPoint[]
  xLabel: string
  yLabel: string
  referenceLine?: 'identity' | 'zero'
}

const WIDTH = 480
const HEIGHT = 260
const PADDING = 36

export function ScatterChart({ points, xLabel, yLabel, referenceLine }: ScatterChartProps) {
  if (points.length === 0) {
    return <p className="text-sm text-muted-foreground">No data to chart.</p>
  }

  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const xMin = Math.min(...xs)
  const xMax = Math.max(...xs)
  const yMin = Math.min(...ys)
  const yMax = Math.max(...ys)

  const xRange = xMax - xMin || 1
  const yRange = yMax - yMin || 1

  const scaleX = (x: number) => PADDING + ((x - xMin) / xRange) * (WIDTH - PADDING * 1.5)
  const scaleY = (y: number) => HEIGHT - PADDING - ((y - yMin) / yRange) * (HEIGHT - PADDING * 1.5)

  let referencePath: string | null = null
  if (referenceLine === 'identity') {
    const lo = Math.max(xMin, yMin)
    const hi = Math.min(xMax, yMax)
    if (lo < hi) referencePath = `M ${scaleX(lo)} ${scaleY(lo)} L ${scaleX(hi)} ${scaleY(hi)}`
  } else if (referenceLine === 'zero' && yMin <= 0 && yMax >= 0) {
    referencePath = `M ${scaleX(xMin)} ${scaleY(0)} L ${scaleX(xMax)} ${scaleY(0)}`
  }

  return (
    <div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full text-muted-foreground"
        role="img"
        aria-label={`${yLabel} versus ${xLabel} scatter plot`}
      >
        {referencePath && (
          <path
            d={referencePath}
            stroke="currentColor"
            className="text-muted-foreground/50"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            fill="none"
          />
        )}
        <line
          x1={PADDING}
          y1={HEIGHT - PADDING}
          x2={WIDTH - PADDING / 4}
          y2={HEIGHT - PADDING}
          className="stroke-border"
          strokeWidth={1}
        />
        <line
          x1={PADDING}
          y1={PADDING / 4}
          x2={PADDING}
          y2={HEIGHT - PADDING}
          className="stroke-border"
          strokeWidth={1}
        />
        {points.map((point, index) => (
          <circle
            key={index}
            cx={scaleX(point.x)}
            cy={scaleY(point.y)}
            r={4}
            className="fill-primary/70"
          >
            <title>{`${xLabel}: ${point.x.toFixed(2)} · ${yLabel}: ${point.y.toFixed(2)}`}</title>
          </circle>
        ))}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>{xLabel} →</span>
        <span>↑ {yLabel}</span>
      </div>
    </div>
  )
}
