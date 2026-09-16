import { Download, Trophy } from 'lucide-react'

import { BarList } from '@/components/bar-list'
import { ConfusionMatrixView } from '@/components/confusion-matrix-view'
import { PcaScatterChart } from '@/components/pca-scatter-chart'
import { ScatterChart } from '@/components/scatter-chart'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import {
  getExperimentDownloadUrl,
  getModelDownloadUrl,
  isClassificationCharts,
  isClusteringCharts,
  type ModelResult,
  type TaskType,
  type TrainingResponse,
} from '@/lib/api'

interface MetricColumn {
  key: string
  label: string
  format: (value: number) => string
}

const METRIC_COLUMNS_BY_TASK: Partial<Record<TaskType, MetricColumn[]>> = {
  regression: [
    { key: 'mae', label: 'MAE', format: (v) => v.toFixed(2) },
    { key: 'rmse', label: 'RMSE', format: (v) => v.toFixed(2) },
    { key: 'r2', label: 'R²', format: (v) => v.toFixed(3) },
  ],
  classification: [
    { key: 'accuracy', label: 'Accuracy', format: (v) => v.toFixed(3) },
    { key: 'precision', label: 'Precision', format: (v) => v.toFixed(3) },
    { key: 'recall', label: 'Recall', format: (v) => v.toFixed(3) },
    { key: 'f1', label: 'F1', format: (v) => v.toFixed(3) },
  ],
  clustering: [
    { key: 'silhouette', label: 'Silhouette', format: (v) => v.toFixed(3) },
    { key: 'davies_bouldin', label: 'Davies–Bouldin', format: (v) => v.toFixed(3) },
    { key: 'n_clusters', label: 'Clusters', format: (v) => v.toFixed(0) },
    { key: 'noise_points', label: 'Noise points', format: (v) => v.toFixed(0) },
  ],
}

export function TrainingResults({ response }: { response: TrainingResponse }) {
  const winner = response.results.find((r) => r.key === response.winner_key) ?? null
  const metricColumns = METRIC_COLUMNS_BY_TASK[response.task] ?? []

  return (
    <div className="space-y-6" role="status" aria-live="polite">
      <Card>
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle>Model comparison</CardTitle>
            <CardDescription>
              {response.task === 'clustering'
                ? `Clustered ${response.train_rows.toLocaleString()} rows directly (no held-out test split — clustering has no ground truth to evaluate against).`
                : `Trained on ${response.train_rows.toLocaleString()} rows, evaluated on ${response.test_rows.toLocaleString()} held-out rows.`}{' '}
              Primary metric: {response.primary_metric.toUpperCase()}{' '}
              {response.primary_metric === 'rmse' ? '(lower is better)' : '(higher is better)'}. The
              best-performing model among these three tested models is highlighted — not necessarily
              the best possible algorithm for this dataset.
              {response.task === 'clustering' &&
                ' Clustering has no known correct answer to compare against, so these scores measure how well-separated the discovered groups are internally.'}
            </CardDescription>
          </div>
          {response.experiment_id && (
            <Button asChild variant="outline" size="sm" className="shrink-0">
              <a href={getExperimentDownloadUrl(response.experiment_id)} download>
                <Download /> Download complete experiment
              </a>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <div className="overflow-auto rounded-md border border-border">
            <table className="w-full min-w-max text-sm">
              <thead className="bg-muted">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Model
                  </th>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Status
                  </th>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Duration
                  </th>
                  {metricColumns.map((column) => (
                    <th key={column.key} scope="col" className="px-3 py-2 text-left font-medium">
                      {column.label}
                    </th>
                  ))}
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Best parameters
                  </th>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Export
                  </th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((result) => (
                  <ModelRow
                    key={result.key}
                    result={result}
                    metricColumns={metricColumns}
                    isWinner={result.key === response.winner_key}
                    experimentId={response.experiment_id}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {winner?.charts && (
        <Card>
          <CardHeader className="flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-4 w-4 text-primary" aria-hidden="true" />
                Best model: {winner.display_name}
              </CardTitle>
              <CardDescription>
                Best-performing model among the tested models, not necessarily the best possible
                algorithm for this dataset.
              </CardDescription>
            </div>
            {response.experiment_id && (
              <Button asChild size="sm" className="shrink-0">
                <a href={getModelDownloadUrl(response.experiment_id, winner.key)} download>
                  <Download /> Download best model
                </a>
              </Button>
            )}
          </CardHeader>
          <CardContent className="grid gap-8 sm:grid-cols-2">
            {isClassificationCharts(winner.charts) ? (
              <div className="sm:col-span-2">
                <h4 className="mb-2 text-sm font-medium text-foreground">Confusion matrix</h4>
                <ConfusionMatrixView confusion={winner.charts.confusion_matrix} />
              </div>
            ) : isClusteringCharts(winner.charts) ? (
              <>
                <div>
                  <h4 className="mb-2 text-sm font-medium text-foreground">
                    Cluster projection (PCA)
                  </h4>
                  <PcaScatterChart points={winner.charts.pca_projection} />
                </div>
                <div>
                  <h4 className="mb-2 text-sm font-medium text-foreground">Cluster sizes</h4>
                  <BarList
                    items={winner.charts.cluster_sizes.map((c) => ({
                      label: `Cluster ${c.cluster}`,
                      count: c.size,
                    }))}
                  />
                  {(winner.metrics?.noise_points ?? 0) > 0 && (
                    <p className="mt-3 text-xs text-muted-foreground">
                      {winner.metrics?.noise_points} point
                      {winner.metrics?.noise_points === 1 ? '' : 's'} didn't fit clearly into any
                      cluster and were marked as noise (shown in gray in the projection above) —
                      excluded from both the cluster sizes and the internal scores.
                    </p>
                  )}
                </div>
              </>
            ) : (
              <>
                <div>
                  <h4 className="mb-2 text-sm font-medium text-foreground">Actual vs. predicted</h4>
                  <ScatterChart
                    points={winner.charts.actual_vs_predicted.map((p) => ({
                      x: p.actual,
                      y: p.predicted,
                    }))}
                    xLabel="Actual"
                    yLabel="Predicted"
                    referenceLine="identity"
                  />
                </div>
                <div>
                  <h4 className="mb-2 text-sm font-medium text-foreground">Residuals</h4>
                  <ScatterChart
                    points={winner.charts.residuals.map((p) => ({ x: p.predicted, y: p.residual }))}
                    xLabel="Predicted"
                    yLabel="Residual"
                    referenceLine="zero"
                  />
                </div>
              </>
            )}
            {winner.feature_importances && (
              <div className="sm:col-span-2">
                <h4 className="mb-2 text-sm font-medium text-foreground">Feature importance</h4>
                <BarList
                  items={[...winner.feature_importances]
                    .sort((a, b) => b.importance - a.importance)
                    .map((f) => ({
                      label: f.feature,
                      count: Math.round(f.importance * 1000) / 1000,
                    }))}
                />
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function ModelRow({
  result,
  metricColumns,
  isWinner,
  experimentId,
}: {
  result: ModelResult
  metricColumns: MetricColumn[]
  isWinner: boolean
  experimentId: string | null
}) {
  const canDownload = result.status === 'success' && experimentId !== null

  return (
    <tr className={cn('border-t border-border', isWinner && 'bg-primary/5')}>
      <td className="px-3 py-1.5 font-medium text-foreground">
        <div className="flex items-center gap-2">
          {result.display_name}
          {isWinner && (
            <Badge variant="success" className="gap-1">
              <Trophy className="h-3 w-3" /> Best
            </Badge>
          )}
        </div>
      </td>
      <td className="px-3 py-1.5">
        {result.status === 'success' ? (
          <Badge variant="success">Success</Badge>
        ) : (
          <Badge variant="destructive">Failed</Badge>
        )}
      </td>
      <td className="px-3 py-1.5 text-muted-foreground">{result.duration_seconds.toFixed(2)}s</td>
      {metricColumns.map((column) => (
        <td key={column.key} className="px-3 py-1.5">
          {result.metrics && column.key in result.metrics
            ? column.format(result.metrics[column.key])
            : '—'}
        </td>
      ))}
      <td className="px-3 py-1.5 text-xs text-muted-foreground">
        {result.best_params
          ? Object.entries(result.best_params)
              .map(([key, value]) => `${key}=${String(value)}`)
              .join(', ')
          : (result.warning ?? '—')}
      </td>
      <td className="px-3 py-1.5">
        {canDownload ? (
          <Button asChild variant="ghost" size="sm">
            <a
              href={getModelDownloadUrl(experimentId, result.key)}
              download
              aria-label={`Download ${result.display_name}`}
            >
              <Download />
            </a>
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </td>
    </tr>
  )
}
