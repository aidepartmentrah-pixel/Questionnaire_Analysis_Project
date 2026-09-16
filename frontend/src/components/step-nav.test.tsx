import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { StepNav } from '@/components/step-nav'

describe('StepNav', () => {
  it('marks steps before the current one as complete and the current one as current', () => {
    render(<StepNav currentStep="configure" />)

    expect(screen.getByText('Configure').closest('div')).toHaveAttribute('aria-current', 'step')
  })

  it('makes completed steps clickable and calls onStepClick with that step', async () => {
    const onStepClick = vi.fn()
    const user = userEvent.setup()
    render(<StepNav currentStep="train" onStepClick={onStepClick} />)

    await user.click(screen.getByRole('button', { name: /go back to upload/i }))

    expect(onStepClick).toHaveBeenCalledWith('upload')
  })

  it('does not make the current or future steps clickable', () => {
    render(<StepNav currentStep="configure" onStepClick={vi.fn()} />)

    expect(screen.queryByRole('button', { name: /go back to configure/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /go back to train/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /go back to results/i })).not.toBeInTheDocument()
  })

  it('renders every step as plain text (no clicking) when onStepClick is not provided', () => {
    render(<StepNav currentStep="train" />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
