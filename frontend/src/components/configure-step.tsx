import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Select } from '@/components/ui/select'
import { getDefaultFeatures, isConfigComplete } from '@/lib/configure'
import { cn } from '@/lib/utils'
import {
  ApiError,
  getPreprocessingPreview,
  type DatasetSummary,
  type PreprocessingPreview,
  type PreprocessingRequest,
  type ScalerType,
  type TaskType,
} from '@/lib/api'

interface ConfigureStepProps {
  dataset: DatasetSummary
  /** Called with the current request whenever it's ready to train, or null otherwise. */
  onReadyChange?: (request: PreprocessingRequest | null) => void
}

const TASK_OPTIONS: { value: TaskType; label: string; description: string }[] = [
  { value: 'regression', label: 'Regression', description: 'Predict a continuous number.' },
  {
    value: 'classification',
    label: 'Classification',
    description: 'Predict a category or label.',
  },
  { value: 'clustering', label: 'Clustering', description: 'Group similar rows without a target.' },
]

type PreviewState =
  | { status: 'incomplete' }
  | { status: 'loading' }
  | { status: 'success'; preview: PreprocessingPreview }
  | { status: 'error'; message: string }

const PREVIEW_DEBOUNCE_MS = 350

export function ConfigureStep({ dataset, onReadyChange }: ConfigureStepProps) {
  const [task, setTask] = useState<TaskType>('regression')
  const [target, setTarget] = useState<string | null>(null)
  const [selectedFeatures, setSelectedFeatures] = useState<Set<string>>(
    () => new Set(getDefaultFeatures('regression', dataset.columns, null, dataset.row_count)),
  )
  const [dropDuplicates, setDropDuplicates] = useState(true)
  const [scaler, setScaler] = useState<ScalerType>('standard')
  const [preview, setPreview] = useState<PreviewState>({ status: 'incomplete' })

  const handleTaskChange = (nextTask: TaskType) => {
    setTask(nextTask)
    const nextTarget = nextTask === 'clustering' ? null : target
    setTarget(nextTarget)
    setSelectedFeatures(
      new Set(getDefaultFeatures(nextTask, dataset.columns, nextTarget, dataset.row_count)),
    )
  }

  const handleTargetChange = (raw: string) => {
    const nextTarget = raw || null
    setTarget(nextTarget)
    setSelectedFeatures(
      new Set(getDefaultFeatures(task, dataset.columns, nextTarget, dataset.row_count)),
    )
  }

  const toggleFeature = (name: string) => {
    setSelectedFeatures((prev) => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }

  const featuresList = useMemo(() => [...selectedFeatures].sort(), [selectedFeatures])
  const featuresKey = featuresList.join(',')

  useEffect(() => {
    if (!isConfigComplete(task, target, featuresList)) {
      setPreview({ status: 'incomplete' })
      onReadyChange?.(null)
      return
    }

    const controller = new AbortController()
    setPreview({ status: 'loading' })

    const request: PreprocessingRequest = {
      task,
      target,
      features: featuresList,
      drop_duplicates: dropDuplicates,
      scaler,
    }

    const timer = setTimeout(() => {
      getPreprocessingPreview(dataset.dataset_id, request, controller.signal)
        .then((result) => {
          setPreview({ status: 'success', preview: result })
          onReadyChange?.(result.ready_to_train ? request : null)
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          const message =
            error instanceof ApiError
              ? error.message
              : 'Could not compute the preprocessing preview.'
          setPreview({ status: 'error', message })
          onReadyChange?.(null)
        })
    }, PREVIEW_DEBOUNCE_MS)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
    // featuresKey is a stable stand-in for featuresList, which is a new array every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset.dataset_id, task, target, featuresKey, dropDuplicates, scaler, onReadyChange])

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Task</CardTitle>
          <CardDescription>
            Selecting a task launches its three matching models when training starts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="radiogroup"
            aria-label="Machine learning task"
            className="grid gap-3 sm:grid-cols-3"
          >
            {TASK_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={task === option.value}
                onClick={() => handleTaskChange(option.value)}
                className={cn(
                  'rounded-lg border p-3 text-left transition-colors',
                  task === option.value
                    ? 'border-primary bg-primary/5 ring-1 ring-primary'
                    : 'border-border hover:bg-accent',
                )}
              >
                <div className="text-sm font-medium text-foreground">{option.label}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{option.description}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {task !== 'clustering' && (
        <Card>
          <CardHeader>
            <CardTitle>Target</CardTitle>
            <CardDescription>The column the model should predict.</CardDescription>
          </CardHeader>
          <CardContent>
            <Select
              aria-label="Target column"
              value={target ?? ''}
              onChange={(event) => handleTargetChange(event.target.value)}
            >
              <option value="">Select a target column…</option>
              {dataset.columns.map((column) => (
                <option key={column.name} value={column.name}>
                  {column.name}
                </option>
              ))}
            </Select>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Features</CardTitle>
          <CardDescription>
            {task === 'clustering'
              ? 'Clustering only supports numeric features in this version.'
              : 'All columns except the target are selected by default (identifier-like columns, e.g. an ID with a unique value per row, are excluded).'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="max-h-64 space-y-1 overflow-auto rounded-md border border-border p-2">
            {dataset.columns
              .filter((column) => column.name !== target)
              .map((column) => {
                const disabled = task === 'clustering' && column.dtype === 'categorical'
                return (
                  <label
                    key={column.name}
                    className={cn(
                      'flex items-center gap-2 rounded px-2 py-1.5 text-sm',
                      disabled ? 'opacity-50' : 'hover:bg-accent',
                    )}
                  >
                    <Checkbox
                      checked={selectedFeatures.has(column.name) && !disabled}
                      disabled={disabled}
                      onChange={() => toggleFeature(column.name)}
                    />
                    <span className="flex-1 text-foreground">{column.name}</span>
                    <Badge variant="outline" className="font-normal">
                      {column.dtype}
                    </Badge>
                  </label>
                )
              })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preprocessing</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-6">
          <label className="flex items-center gap-2 text-sm text-foreground">
            <Checkbox
              checked={dropDuplicates}
              onChange={(event) => setDropDuplicates(event.target.checked)}
            />
            Remove duplicate rows
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            Scaling
            <Select
              value={scaler}
              onChange={(event) => setScaler(event.target.value as ScalerType)}
            >
              <option value="none">None</option>
              <option value="standard">Standard</option>
              <option value="minmax">Min-Max</option>
            </Select>
          </label>
        </CardContent>
      </Card>

      <PreprocessingImpact state={preview} />
    </div>
  )
}

function ImpactStat({
  label,
  value,
  emphasize,
}: {
  label: string
  value: number
  emphasize?: boolean
}) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className={cn('text-lg font-semibold', emphasize ? 'text-primary' : 'text-foreground')}>
        {value.toLocaleString()}
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

function PreprocessingImpact({ state }: { state: PreviewState }) {
  if (state.status === 'incomplete') {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Complete the configuration above to see the preprocessing impact.
        </CardContent>
      </Card>
    )
  }

  if (state.status === 'loading') {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Computing preprocessing impact…
        </CardContent>
      </Card>
    )
  }

  if (state.status === 'error') {
    return (
      <Card>
        <CardContent className="py-8">
          <div role="alert" className="text-sm text-destructive">
            {state.message}
          </div>
        </CardContent>
      </Card>
    )
  }

  const { preview } = state

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Preprocessing impact</CardTitle>
          <CardDescription>Preview of what training will actually see.</CardDescription>
        </div>
        {preview.ready_to_train ? (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" /> Ready to train
          </Badge>
        ) : (
          <Badge variant="destructive" className="gap-1">
            <AlertTriangle className="h-3.5 w-3.5" /> Not ready
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <ImpactStat label="Original rows" value={preview.original_rows} />
          <ImpactStat label="Removed (missing)" value={preview.removed_missing_rows} />
          <ImpactStat label="Removed (duplicates)" value={preview.removed_duplicate_rows} />
          <ImpactStat label="Final rows" value={preview.final_rows} emphasize />
        </div>

        {preview.warnings.length > 0 && (
          <ul className="space-y-1">
            {preview.warnings.map((warning) => (
              <li
                key={warning}
                data-testid="config-warning"
                className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/5 p-2 text-xs text-warning"
              >
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {warning}
              </li>
            ))}
          </ul>
        )}

        <div>
          <h4 className="mb-1.5 text-xs font-medium text-muted-foreground">
            Final feature columns ({preview.final_feature_columns.length})
          </h4>
          <div className="flex flex-wrap gap-1">
            {preview.final_feature_columns.map((name) => (
              <Badge key={name} variant="secondary" className="font-normal">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
