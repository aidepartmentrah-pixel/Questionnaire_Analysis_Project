import type { PcaPoint } from '@/lib/api'

interface PcaScatterChartProps {
  points: PcaPoint[]
}

const WIDTH = 480
const HEIGHT = 300
const PADDING = 36

// A small fixed categorical order (never cycled per-render, never reassigned
// by rank) plus a dedicated muted color for DBSCAN noise points, which are
// not a cluster and shouldn't read as one.
const CLUSTER_COLORS = ['#2563eb', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
const NOISE_COLOR = '#9ca3af'
const NOISE_LABEL = '-1'

function colorForCluster(cluster: string, clusterOrder: string[]): string {
  const index = clusterOrder.indexOf(cluster)
  return CLUSTER_COLORS[index % CLUSTER_COLORS.length] ?? NOISE_COLOR
}

export function PcaScatterChart({ points }: PcaScatterChartProps) {
  if (points.length === 0) {
    return <p className="text-sm text-muted-foreground">No data to chart.</p>
  }

  const clusterOrder = [...new Set(points.map((p) => p.cluster))]
    .filter((c) => c !== NOISE_LABEL)
    .sort()
  const hasNoise = points.some((p) => p.cluster === NOISE_LABEL)

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

  return (
    <div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full text-muted-foreground"
        role="img"
        aria-label="Two-dimensional PCA projection of the clustering result"
      >
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
        {points.map((point, index) => {
          const isNoise = point.cluster === NOISE_LABEL
          const color = isNoise ? NOISE_COLOR : colorForCluster(point.cluster, clusterOrder)
          return (
            <circle
              key={index}
              cx={scaleX(point.x)}
              cy={scaleY(point.y)}
              r={isNoise ? 3 : 4}
              fill={color}
              fillOpacity={isNoise ? 0.45 : 0.8}
            >
              <title>
                {isNoise ? 'Noise point' : `Cluster ${point.cluster}`} (PC1: {point.x.toFixed(2)},
                PC2: {point.y.toFixed(2)})
              </title>
            </circle>
          )
        })}
      </svg>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span>PC1 →</span>
        <span>↑ PC2</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {clusterOrder.map((cluster) => (
          <span key={cluster} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: colorForCluster(cluster, clusterOrder) }}
              aria-hidden="true"
            />
            Cluster {cluster}
          </span>
        ))}
        {hasNoise && (
          <span className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: NOISE_COLOR }}
              aria-hidden="true"
            />
            Noise
          </span>
        )}
      </div>
    </div>
  )
}
