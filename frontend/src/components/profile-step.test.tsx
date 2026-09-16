import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ProfileStep } from '@/components/profile-step'
import * as api from '@/lib/api'
import type { DatasetProfile } from '@/lib/api'

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    getDatasetProfile: vi.fn(),
  }
})

const mockedGetDatasetProfile = vi.mocked(api.getDatasetProfile)

function buildProfile(overrides: Partial<DatasetProfile> = {}): DatasetProfile {
  return {
    dataset_id: 'abc123',
    filename: 'customer_segments.csv',
    row_count: 222,
    column_count: 8,
    duplicate_row_count: 2,
    columns: [
      {
        name: 'age',
        dtype: 'numeric',
        pandas_dtype: 'int64',
        missing_count: 0,
        missing_percentage: 0,
        unique_count: 48,
      },
      {
        name: 'region',
        dtype: 'categorical',
        pandas_dtype: 'object',
        missing_count: 2,
        missing_percentage: 0.9,
        unique_count: 4,
      },
    ],
    numeric_summary: [
      {
        column: 'age',
        count: 222,
        mean: 40.1,
        std: 12.3,
        min: 18,
        q25: 28,
        median: 39,
        q75: 52,
        max: 75,
      },
    ],
    numeric_distributions: [
      {
        column: 'age',
        bins: [
          { bin_start: 18, bin_end: 24, count: 20 },
          { bin_start: 24, bin_end: 30, count: 35 },
        ],
      },
    ],
    categorical_frequencies: [
      {
        column: 'region',
        truncated: false,
        categories: [
          { value: 'North', count: 60 },
          { value: 'South', count: 55 },
        ],
      },
    ],
    correlation: {
      columns: ['age'],
      matrix: [[1]],
    },
    ...overrides,
  }
}

describe('ProfileStep', () => {
  beforeEach(() => {
    mockedGetDatasetProfile.mockReset()
  })

  it('shows a loading state while the profile is being fetched', () => {
    mockedGetDatasetProfile.mockReturnValue(new Promise(() => {}))

    render(<ProfileStep datasetId="abc123" />)

    expect(screen.getByText(/loading profile/i)).toBeInTheDocument()
  })

  it('renders overview cards, column table, charts and the correlation heatmap on success', async () => {
    mockedGetDatasetProfile.mockResolvedValue(buildProfile())

    render(<ProfileStep datasetId="abc123" />)

    expect(await screen.findByText('customer_segments.csv')).toBeInTheDocument()
    expect(screen.getByText('222')).toBeInTheDocument()
    expect(screen.getAllByText('age').length).toBeGreaterThan(0)
    expect(screen.getAllByText('region').length).toBeGreaterThan(0)
    expect(screen.getByText('North')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /download eda report/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/datasets/abc123/profile/report'),
    )
  })

  it('shows empty-chart messaging when there is nothing to chart', async () => {
    mockedGetDatasetProfile.mockResolvedValue(
      buildProfile({ numeric_distributions: [], categorical_frequencies: [], correlation: null }),
    )

    render(<ProfileStep datasetId="abc123" />)

    expect(await screen.findByText(/no numeric columns to chart/i)).toBeInTheDocument()
    expect(
      screen.getByText(/no categorical columns with a suitable number of categories/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/not enough numeric columns for a correlation matrix/i),
    ).toBeInTheDocument()
  })

  it('shows a friendly error message when the profile fails to load', async () => {
    mockedGetDatasetProfile.mockRejectedValue(new api.ApiError('Dataset not found.', 404))

    render(<ProfileStep datasetId="missing" />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Dataset not found.')
  })
})
