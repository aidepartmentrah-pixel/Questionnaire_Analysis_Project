import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ConfigureStep } from '@/components/configure-step'
import * as api from '@/lib/api'
import type { DatasetSummary, PreprocessingPreview } from '@/lib/api'

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    getPreprocessingPreview: vi.fn(),
  }
})

const mockedGetPreprocessingPreview = vi.mocked(api.getPreprocessingPreview)

const DATASET: DatasetSummary = {
  dataset_id: 'abc123',
  filename: 'customer_segments.csv',
  row_count: 222,
  column_count: 4,
  preview_row_count: 5,
  preview: [],
  columns: [
    { name: 'age', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 48 },
    { name: 'income', dtype: 'numeric', pandas_dtype: 'float64', unique_count: 200 },
    { name: 'region', dtype: 'categorical', pandas_dtype: 'object', unique_count: 4 },
    { name: 'churned', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 2 },
  ],
}

function buildPreview(overrides: Partial<PreprocessingPreview> = {}): PreprocessingPreview {
  return {
    dataset_id: 'abc123',
    task: 'classification',
    target: 'churned',
    features: ['age', 'income', 'region'],
    original_rows: 222,
    removed_missing_rows: 6,
    removed_duplicate_rows: 2,
    final_rows: 214,
    final_feature_columns: ['age', 'income', 'region_East', 'region_North'],
    ready_to_train: true,
    warnings: [],
    ...overrides,
  }
}

describe('ConfigureStep', () => {
  beforeEach(() => {
    mockedGetPreprocessingPreview.mockReset()
  })

  it('shows the preprocessing impact once a target and features are chosen', async () => {
    mockedGetPreprocessingPreview.mockResolvedValue(buildPreview())

    const user = userEvent.setup()
    render(<ConfigureStep dataset={DATASET} />)

    expect(
      screen.getByText(/complete the configuration above to see the preprocessing impact/i),
    ).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Target column'), 'churned')

    expect(await screen.findByText(/ready to train/i, {}, { timeout: 2000 })).toBeInTheDocument()
    expect(screen.getByText('214')).toBeInTheDocument()
    expect(mockedGetPreprocessingPreview).toHaveBeenCalledWith(
      'abc123',
      expect.objectContaining({ task: 'regression', target: 'churned' }),
      expect.anything(),
    )
  })

  it('hides the target selector and disables categorical features for clustering', async () => {
    mockedGetPreprocessingPreview.mockResolvedValue(
      buildPreview({ task: 'clustering', target: null, features: ['age', 'income'] }),
    )

    const user = userEvent.setup()
    render(<ConfigureStep dataset={DATASET} />)

    await user.click(screen.getByRole('radio', { name: /clustering/i }))

    expect(screen.queryByLabelText('Target column')).not.toBeInTheDocument()

    const regionRow = screen.getByText('region').closest('label')
    expect(regionRow).not.toBeNull()
    expect(regionRow?.querySelector('input[type="checkbox"]')).toBeDisabled()

    expect(await screen.findByText(/ready to train/i, {}, { timeout: 2000 })).toBeInTheDocument()
  })

  it('shows a friendly error message when the preview request fails', async () => {
    mockedGetPreprocessingPreview.mockRejectedValue(
      new api.ApiError('Clustering only supports numeric features in this version.', 422),
    )

    const user = userEvent.setup()
    render(<ConfigureStep dataset={DATASET} />)

    await user.selectOptions(screen.getByLabelText('Target column'), 'churned')

    expect(await screen.findByRole('alert', {}, { timeout: 2000 })).toHaveTextContent(
      'Clustering only supports numeric features in this version.',
    )
  })
})
