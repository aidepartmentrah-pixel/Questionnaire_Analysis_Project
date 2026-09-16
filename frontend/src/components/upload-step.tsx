import { useState } from 'react'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

import { DatasetPreviewTable } from '@/components/dataset-preview-table'
import { FileDropzone } from '@/components/file-dropzone'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ApiError, uploadDataset, type DatasetSummary } from '@/lib/api'

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading'; filename: string; progress: number }
  | { status: 'success'; dataset: DatasetSummary }
  | { status: 'error'; message: string }

interface UploadStepProps {
  onUploaded?: (dataset: DatasetSummary) => void
}

export function UploadStep({ onUploaded }: UploadStepProps) {
  const [state, setState] = useState<UploadState>({ status: 'idle' })

  const handleFileSelected = (file: File) => {
    setState({ status: 'uploading', filename: file.name, progress: 0 })

    uploadDataset(file, {
      onProgress: (progress) => setState({ status: 'uploading', filename: file.name, progress }),
    })
      .then((dataset) => {
        setState({ status: 'success', dataset })
        onUploaded?.(dataset)
      })
      .catch((error: unknown) => {
        const message =
          error instanceof ApiError
            ? error.message
            : 'Something went wrong while uploading the file.'
        setState({ status: 'error', message })
      })
  }

  const isUploading = state.status === 'uploading'

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a dataset</CardTitle>
        <CardDescription>
          Bring in a CSV file to begin exploring and modeling your data. Uploading a new file
          replaces the active dataset.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {state.status === 'uploading' && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <p className="text-sm font-medium text-foreground">Uploading {state.filename}…</p>
            <Progress value={state.progress} />
          </div>
        )}

        {state.status === 'error' && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p>{state.message}</p>
          </div>
        )}

        {state.status === 'success' && (
          <div
            role="status"
            data-testid="dataset-summary"
            className="flex items-start gap-2 rounded-md border border-success/30 bg-success/5 p-4"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">{state.dataset.filename}</p>
              <p className="text-xs text-muted-foreground">
                {state.dataset.row_count.toLocaleString()} rows &middot;{' '}
                {state.dataset.column_count} columns
              </p>
            </div>
          </div>
        )}

        <FileDropzone
          onFileSelected={handleFileSelected}
          disabled={isUploading}
          hint="CSV files up to 25 MB."
          label={
            state.status === 'success'
              ? 'Drop a new CSV file to replace this dataset'
              : 'Drag and drop a CSV file here'
          }
        />

        {state.status === 'success' && (
          <div>
            <h4 className="mb-2 text-sm font-medium text-foreground">
              Preview (first {state.dataset.preview_row_count} of{' '}
              {state.dataset.row_count.toLocaleString()} rows)
            </h4>
            <DatasetPreviewTable columns={state.dataset.columns} rows={state.dataset.preview} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
