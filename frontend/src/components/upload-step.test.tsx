import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { UploadStep } from '@/components/upload-step'
import * as api from '@/lib/api'

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    uploadDataset: vi.fn(),
  }
})

const mockedUploadDataset = vi.mocked(api.uploadDataset)

function makeCsvFile(name = 'data.csv') {
  return new File(['a,b\n1,2\n'], name, { type: 'text/csv' })
}

describe('UploadStep', () => {
  beforeEach(() => {
    mockedUploadDataset.mockReset()
  })

  it('shows the dataset summary and preview table after a successful upload', async () => {
    mockedUploadDataset.mockResolvedValue({
      dataset_id: 'abc123',
      filename: 'customer_segments.csv',
      row_count: 222,
      column_count: 2,
      columns: [
        { name: 'a', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 2 },
        { name: 'b', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 2 },
      ],
      preview: [{ a: 1, b: 2 }],
      preview_row_count: 1,
    })

    const user = userEvent.setup()
    render(<UploadStep />)

    const input = screen.getByLabelText(/upload csv file/i)
    await user.upload(input, makeCsvFile())

    expect(await screen.findByText('customer_segments.csv')).toBeInTheDocument()
    expect(screen.getByText(/2 columns/i)).toBeInTheDocument()
    expect(screen.getByText(/preview \(first 1 of 222 rows\)/i)).toBeInTheDocument()
    expect(screen.getByText('a')).toBeInTheDocument()
    expect(screen.getByText(/drop a new csv file to replace this dataset/i)).toBeInTheDocument()
  })

  it('shows a friendly error message when the upload is rejected', async () => {
    mockedUploadDataset.mockRejectedValue(new api.ApiError('The uploaded file is empty.', 422))

    const user = userEvent.setup()
    render(<UploadStep />)

    const input = screen.getByLabelText(/upload csv file/i)
    await user.upload(input, makeCsvFile('empty.csv'))

    expect(await screen.findByRole('alert')).toHaveTextContent('The uploaded file is empty.')
  })

  it('replaces a previously uploaded dataset with a newly uploaded one', async () => {
    mockedUploadDataset.mockResolvedValueOnce({
      dataset_id: 'first',
      filename: 'first.csv',
      row_count: 10,
      column_count: 1,
      columns: [{ name: 'a', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 2 }],
      preview: [{ a: 1 }],
      preview_row_count: 1,
    })

    const user = userEvent.setup()
    render(<UploadStep />)

    const input = screen.getByLabelText(/upload csv file/i)
    await user.upload(input, makeCsvFile('first.csv'))
    expect(await screen.findByText('first.csv')).toBeInTheDocument()

    mockedUploadDataset.mockResolvedValueOnce({
      dataset_id: 'second',
      filename: 'second.csv',
      row_count: 20,
      column_count: 1,
      columns: [{ name: 'a', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 2 }],
      preview: [{ a: 2 }],
      preview_row_count: 1,
    })

    await user.upload(input, makeCsvFile('second.csv'))

    expect(await screen.findByText('second.csv')).toBeInTheDocument()
    expect(screen.queryByText('first.csv')).not.toBeInTheDocument()
    expect(mockedUploadDataset).toHaveBeenCalledTimes(2)
  })
})
