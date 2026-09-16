import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'

import { BarList } from '@/components/bar-list'
import { CorrelationHeatmap } from '@/components/correlation-heatmap'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ApiError,
  getDatasetProfile,
  getEdaReportUrl,
  type DatasetProfile,
  type HistogramBin,
} from '@/lib/api'

function formatBinLabel(bin: HistogramBin): string {
  const format = (value: number) => (Number.isInteger(value) ? value.toString() : value.toFixed(1))
  return bin.bin_start === bin.bin_end
    ? format(bin.bin_start)
    : `${format(bin.bin_start)}–${format(bin.bin_end)}`
}

interface ProfileStepProps {
  /** Render with `key={datasetId}` so a new dataset id remounts (and resets) this component. */
  datasetId: string
}

type ProfileState =
  | { status: 'loading' }
  | { status: 'success'; profile: DatasetProfile }
  | { status: 'error'; message: string }

function OverviewCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-lg font-semibold text-foreground">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

export function ProfileStep({ datasetId }: ProfileStepProps) {
  const [state, setState] = useState<ProfileState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    getDatasetProfile(datasetId, controller.signal)
      .then((profile) => setState({ status: 'success', profile }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        const message =
          error instanceof ApiError ? error.message : 'Could not load the dataset profile.'
        setState({ status: 'error', message })
      })

    return () => controller.abort()
  }, [datasetId])

  if (state.status === 'loading') {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Loading profile…
        </CardContent>
      </Card>
    )
  }

  if (state.status === 'error') {
    return (
      <Card>
        <CardContent className="py-10">
          <div role="alert" className="text-sm text-destructive">
            {state.message}
          </div>
        </CardContent>
      </Card>
    )
  }

  const { profile } = state
  const missingCells = profile.columns.reduce((sum, column) => sum + column.missing_count, 0)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Dataset profile</CardTitle>
            <CardDescription>{profile.filename}</CardDescription>
          </div>
          <Button asChild variant="outline" size="sm">
            <a href={getEdaReportUrl(profile.dataset_id)} download>
              <Download /> Download EDA report
            </a>
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <OverviewCard label="Rows" value={profile.row_count.toLocaleString()} />
            <OverviewCard label="Columns" value={profile.column_count.toString()} />
            <OverviewCard label="Duplicate rows" value={profile.duplicate_row_count.toString()} />
            <OverviewCard label="Missing cells" value={missingCells.toLocaleString()} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Columns</CardTitle>
          <CardDescription>
            Detected type, missing values and uniqueness per column.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="overflow-auto rounded-md border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            tabIndex={0}
            role="region"
            aria-label="Column profile table"
          >
            <table className="w-full min-w-max text-sm">
              <thead className="bg-muted">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Column
                  </th>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Type
                  </th>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Missing
                  </th>
                  <th scope="col" className="px-3 py-2 text-left font-medium">
                    Unique
                  </th>
                </tr>
              </thead>
              <tbody>
                {profile.columns.map((column) => (
                  <tr key={column.name} className="border-t border-border">
                    <td className="px-3 py-1.5">{column.name}</td>
                    <td className="px-3 py-1.5">
                      <Badge variant="outline" className="font-normal">
                        {column.dtype}
                      </Badge>
                    </td>
                    <td className="px-3 py-1.5">
                      {column.missing_count} ({column.missing_percentage.toFixed(1)}%)
                    </td>
                    <td className="px-3 py-1.5">{column.unique_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Numeric distributions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {profile.numeric_distributions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No numeric columns to chart.</p>
          ) : (
            profile.numeric_distributions.map((dist) => (
              <div key={dist.column}>
                <h4 className="mb-2 text-sm font-medium text-foreground">{dist.column}</h4>
                <BarList
                  items={dist.bins.map((bin) => ({
                    label: formatBinLabel(bin),
                    count: bin.count,
                  }))}
                />
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Categorical frequencies</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {profile.categorical_frequencies.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No categorical columns with a suitable number of categories to chart.
            </p>
          ) : (
            profile.categorical_frequencies.map((freq) => (
              <div key={freq.column}>
                <h4 className="mb-2 text-sm font-medium text-foreground">
                  {freq.column}
                  {freq.truncated && (
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      (top categories, remainder grouped as "Other")
                    </span>
                  )}
                </h4>
                <BarList items={freq.categories.map((c) => ({ label: c.value, count: c.count }))} />
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Correlation matrix</CardTitle>
          <CardDescription>Pearson correlation between numeric columns.</CardDescription>
        </CardHeader>
        <CardContent>
          {profile.correlation === null ? (
            <p className="text-sm text-muted-foreground">
              Not enough numeric columns for a correlation matrix.
            </p>
          ) : (
            <CorrelationHeatmap correlation={profile.correlation} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
