import { useState } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'

import { TrainingResults } from '@/components/training-results'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ApiError,
  startTraining,
  type DatasetSummary,
  type PreprocessingRequest,
  type TaskType,
  type TrainingResponse,
} from '@/lib/api'

interface TrainStepProps {
  dataset: DatasetSummary
  config: PreprocessingRequest | null
  onComplete?: (response: TrainingResponse) => void
}

type TrainState =
  | { status: 'idle' }
  | { status: 'training' }
  | { status: 'success'; response: TrainingResponse }
  | { status: 'error'; message: string }

// Mirrors app/ml/registry.py's *_MODELS display names, shown while the
// single synchronous training request is in flight.
const MODEL_NAMES_BY_TASK: Partial<Record<TaskType, string[]>> = {
  regression: ['Linear Regression', 'Random Forest Regressor', 'XGBoost Regressor'],
  classification: ['Logistic Regression', 'Random Forest Classifier', 'XGBoost Classifier'],
  clustering: ['K-Means', 'Agglomerative Clustering', 'DBSCAN'],
}

export function TrainStep({ dataset, config, onComplete }: TrainStepProps) {
  const [state, setState] = useState<TrainState>({ status: 'idle' })

  if (!config) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Finish a ready-to-train configuration on the Configure step first.
        </CardContent>
      </Card>
    )
  }

  const modelNames = MODEL_NAMES_BY_TASK[config.task] ?? []

  const handleStart = () => {
    if (state.status === 'training') return // guards against a double-click double-submitting
    setState({ status: 'training' })
    startTraining(dataset.dataset_id, config)
      .then((response) => {
        setState({ status: 'success', response })
        onComplete?.(response)
      })
      .catch((error: unknown) => {
        const message = error instanceof ApiError ? error.message : 'Training failed unexpectedly.'
        setState({ status: 'error', message })
      })
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Train and tune</CardTitle>
          <CardDescription>
            {config.task === 'clustering'
              ? 'The three clustering algorithms are hyperparameter-tuned and fit directly on the complete processed dataset — clustering has no target and no held-out test split.'
              : `The three ${config.task} models are hyperparameter-tuned (3-fold cross-validation on the training split), trained with their best configuration, and evaluated once on a held-out test split.`}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="grid gap-2 sm:grid-cols-3">
            {modelNames.map((name) => (
              <li
                key={name}
                className="flex items-center gap-2 rounded-md border border-border p-3 text-sm text-foreground"
              >
                {state.status === 'training' ? (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
                ) : (
                  <span className="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/40" />
                )}
                {name}
              </li>
            ))}
          </ul>

          <Button
            type="button"
            onClick={handleStart}
            disabled={state.status === 'training'}
            aria-busy={state.status === 'training'}
          >
            {state.status === 'training' ? 'Training…' : 'Start training'}
          </Button>

          {state.status === 'error' && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>{state.message}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {state.status === 'success' && <TrainingResults response={state.response} />}
    </div>
  )
}
