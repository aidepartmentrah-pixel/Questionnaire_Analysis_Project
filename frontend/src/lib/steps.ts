export type StepId = 'upload' | 'profile' | 'configure' | 'train' | 'results'

interface Step {
  id: StepId
  label: string
}

export const WORKFLOW_STEPS: Step[] = [
  { id: 'upload', label: 'Upload' },
  { id: 'profile', label: 'Profile' },
  { id: 'configure', label: 'Configure' },
  { id: 'train', label: 'Train' },
  { id: 'results', label: 'Results' },
]
