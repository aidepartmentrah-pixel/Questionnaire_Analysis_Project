import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { ArrowLeft, ArrowRight } from 'lucide-react'

import { ConfigureStep } from '@/components/configure-step'
import { HealthIndicator } from '@/components/health-indicator'
import { ProfileStep } from '@/components/profile-step'
import { StepNav } from '@/components/step-nav'
import { TrainStep } from '@/components/train-step'
import { TrainingResults } from '@/components/training-results'
import { UploadStep } from '@/components/upload-step'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { DatasetSummary, PreprocessingRequest, TrainingResponse } from '@/lib/api'
import type { StepId } from '@/lib/steps'

function NoDatasetYet({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-10 text-center text-sm text-muted-foreground">
        {message}
      </CardContent>
    </Card>
  )
}

function App() {
  const [currentStep, setCurrentStep] = useState<StepId>('upload')
  const [dataset, setDataset] = useState<DatasetSummary | null>(null)
  const [trainConfig, setTrainConfig] = useState<PreprocessingRequest | null>(null)
  const [trainingResponse, setTrainingResponse] = useState<TrainingResponse | null>(null)

  const mainContentRef = useRef<HTMLDivElement>(null)
  const isFirstRender = useRef(true)

  // Move focus to the new step's content on every navigation (but not on
  // the very first render — that would steal focus on initial page load),
  // so keyboard and screen-reader users get taken to what changed instead
  // of staying anchored to a nav item that's no longer where the action is.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }
    mainContentRef.current?.focus()
  }, [currentStep])

  const handleUploaded = useCallback((uploaded: DatasetSummary) => {
    setDataset(uploaded)
    // A replaced dataset invalidates any configuration/results from the
    // previous one — feature names, target, etc. may no longer even exist.
    setTrainConfig(null)
    setTrainingResponse(null)
  }, [])

  // Must stay referentially stable: it's in ConfigureStep's effect
  // dependency array, and calling it changes App's state, which would
  // otherwise create a new function each render and re-trigger that effect
  // in an infinite loop (verified — this exact bug shipped once already).
  const handleReadyChange = useCallback((request: PreprocessingRequest | null) => {
    setTrainConfig(request)
    // A changed configuration invalidates any previously trained results.
    setTrainingResponse(null)
  }, [])

  const goToStep = useCallback((step: StepId) => setCurrentStep(step), [])

  let content: ReactNode
  if (currentStep === 'upload') {
    content = <UploadStep onUploaded={handleUploaded} />
  } else if (currentStep === 'profile') {
    content = dataset ? (
      <ProfileStep key={dataset.dataset_id} datasetId={dataset.dataset_id} />
    ) : (
      <NoDatasetYet message="Upload a dataset first to see its profile." />
    )
  } else if (currentStep === 'configure') {
    content = dataset ? (
      <ConfigureStep key={dataset.dataset_id} dataset={dataset} onReadyChange={handleReadyChange} />
    ) : (
      <NoDatasetYet message="Upload a dataset first to configure training." />
    )
  } else if (currentStep === 'train') {
    content = dataset ? (
      <TrainStep
        key={dataset.dataset_id + JSON.stringify(trainConfig)}
        dataset={dataset}
        config={trainConfig}
        onComplete={setTrainingResponse}
      />
    ) : (
      <NoDatasetYet message="Upload a dataset first to train models." />
    )
  } else {
    content = trainingResponse ? (
      <TrainingResults response={trainingResponse} />
    ) : (
      <NoDatasetYet message="Train a model first to see results here." />
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">AutoML Studio</h1>
            <p className="text-sm text-muted-foreground">Automated model training and comparison</p>
          </div>
          <HealthIndicator />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8 rounded-lg border border-border bg-card p-4">
          <StepNav currentStep={currentStep} onStepClick={goToStep} />
        </div>

        {/* tabIndex=-1: not in the normal tab order, just a programmatic focus target on step change. */}
        <div ref={mainContentRef} tabIndex={-1} className="focus:outline-none">
          {content}
        </div>

        {currentStep === 'upload' && dataset && (
          <div className="mt-4 flex justify-end">
            <Button type="button" size="sm" onClick={() => goToStep('profile')}>
              Continue to profile <ArrowRight />
            </Button>
          </div>
        )}

        {currentStep === 'profile' && (
          <div className="mt-4 flex justify-between">
            <Button type="button" variant="ghost" size="sm" onClick={() => goToStep('upload')}>
              <ArrowLeft /> Back to upload
            </Button>
            <Button type="button" size="sm" onClick={() => goToStep('configure')}>
              Continue to configure <ArrowRight />
            </Button>
          </div>
        )}

        {currentStep === 'configure' && (
          <div className="mt-4 flex justify-between">
            <Button type="button" variant="ghost" size="sm" onClick={() => goToStep('profile')}>
              <ArrowLeft /> Back to profile
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!trainConfig}
              onClick={() => goToStep('train')}
            >
              Continue to train <ArrowRight />
            </Button>
          </div>
        )}

        {currentStep === 'train' && (
          <div className="mt-4 flex justify-between">
            <Button type="button" variant="ghost" size="sm" onClick={() => goToStep('configure')}>
              <ArrowLeft /> Back to configure
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!trainingResponse}
              onClick={() => goToStep('results')}
            >
              Continue to results <ArrowRight />
            </Button>
          </div>
        )}

        {currentStep === 'results' && (
          <div className="mt-4">
            <Button type="button" variant="ghost" size="sm" onClick={() => goToStep('train')}>
              <ArrowLeft /> Back to train
            </Button>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
