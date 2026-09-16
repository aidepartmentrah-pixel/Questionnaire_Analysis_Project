import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            app_name: 'AutoML Demonstration API',
            environment: 'test',
            version: '0.1.0',
          }),
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the app title and the five-step workflow layout', async () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'AutoML Studio' })).toBeInTheDocument()

    for (const label of ['Upload', 'Profile', 'Configure', 'Train', 'Results']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }

    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
  })

  it('shows an offline indicator when the backend is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network error')))

    render(<App />)

    expect(await screen.findByText('Backend unreachable')).toBeInTheDocument()
  })
})
