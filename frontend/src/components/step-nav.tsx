import { Check } from 'lucide-react'

import { WORKFLOW_STEPS, type StepId } from '@/lib/steps'
import { cn } from '@/lib/utils'

interface StepNavProps {
  currentStep: StepId
  /** Called when the user activates a completed (already-visited) step. Future steps are never clickable. */
  onStepClick?: (step: StepId) => void
}

export function StepNav({ currentStep, onStepClick }: StepNavProps) {
  const currentIndex = WORKFLOW_STEPS.findIndex((step) => step.id === currentStep)

  return (
    <ol className="flex w-full items-center" aria-label="Workflow progress">
      {WORKFLOW_STEPS.map((step, index) => {
        const isComplete = index < currentIndex
        const isCurrent = index === currentIndex

        const badge = (
          <span
            className={cn(
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
              isCurrent && 'border-primary bg-primary text-primary-foreground',
              isComplete && 'border-primary bg-primary/10 text-primary',
              !isCurrent && !isComplete && 'border-border text-muted-foreground',
            )}
            aria-hidden="true"
          >
            {isComplete ? <Check className="h-4 w-4" /> : index + 1}
          </span>
        )

        const label = (
          <span
            className={cn(
              'text-sm font-medium',
              isCurrent ? 'text-foreground' : 'text-muted-foreground',
            )}
          >
            {step.label}
          </span>
        )

        return (
          <li key={step.id} className="flex flex-1 items-center last:flex-none">
            {isComplete && onStepClick ? (
              <button
                type="button"
                onClick={() => onStepClick(step.id)}
                className="flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                aria-label={`Go back to ${step.label}`}
              >
                {badge}
                {label}
              </button>
            ) : (
              <div
                className="flex items-center gap-2"
                aria-current={isCurrent ? 'step' : undefined}
              >
                {badge}
                {label}
              </div>
            )}
            {index < WORKFLOW_STEPS.length - 1 && (
              <div
                className={cn('mx-3 h-px flex-1', isComplete ? 'bg-primary/40' : 'bg-border')}
                aria-hidden="true"
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
