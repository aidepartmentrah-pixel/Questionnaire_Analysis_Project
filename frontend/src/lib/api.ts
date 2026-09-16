export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface HealthResponse {
  status: string
  app_name: string
  environment: string
  version: string
}

export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, { signal })

  if (!response.ok) {
    throw new ApiError(`Health check failed with status ${response.status}`, response.status)
  }

  return (await response.json()) as HealthResponse
}

export interface ColumnInfo {
  name: string
  dtype: 'numeric' | 'categorical'
  pandas_dtype: string
  unique_count: number
}

export interface DatasetSummary {
  dataset_id: string
  filename: string
  row_count: number
  column_count: number
  columns: ColumnInfo[]
  preview: Record<string, unknown>[]
  preview_row_count: number
}

interface UploadDatasetOptions {
  onProgress?: (percent: number) => void
  signal?: AbortSignal
}

/**
 * Uses XMLHttpRequest instead of fetch so we can report real upload
 * progress (fetch has no cross-browser upload-progress event).
 */
export function uploadDataset(
  file: File,
  options: UploadDatasetOptions = {},
): Promise<DatasetSummary> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}/api/datasets/upload`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        options.onProgress?.(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      let body: unknown = null
      try {
        body = JSON.parse(xhr.responseText) as unknown
      } catch {
        body = null
      }

      if (xhr.status >= 200 && xhr.status < 300 && body) {
        resolve(body as DatasetSummary)
        return
      }

      const detail =
        body && typeof body === 'object' && 'detail' in body
          ? String((body as { detail: unknown }).detail)
          : `Upload failed with status ${xhr.status}.`
      reject(new ApiError(detail, xhr.status))
    }

    xhr.onerror = () => reject(new ApiError('Network error while uploading the file.'))
    xhr.onabort = () => reject(new DOMException('Upload aborted', 'AbortError'))

    if (options.signal) {
      if (options.signal.aborted) {
        xhr.abort()
      } else {
        options.signal.addEventListener('abort', () => xhr.abort())
      }
    }

    const formData = new FormData()
    formData.append('file', file)
    xhr.send(formData)
  })
}

export interface ColumnProfile {
  name: string
  dtype: 'numeric' | 'categorical'
  pandas_dtype: string
  missing_count: number
  missing_percentage: number
  unique_count: number
}

export interface NumericSummary {
  column: string
  count: number
  mean: number
  std: number | null
  min: number
  q25: number
  median: number
  q75: number
  max: number
}

export interface HistogramBin {
  bin_start: number
  bin_end: number
  count: number
}

export interface NumericDistribution {
  column: string
  bins: HistogramBin[]
}

export interface CategoryCount {
  value: string
  count: number
}

export interface CategoricalFrequency {
  column: string
  categories: CategoryCount[]
  truncated: boolean
}

export interface CorrelationMatrix {
  columns: string[]
  matrix: (number | null)[][]
}

export interface DatasetProfile {
  dataset_id: string
  filename: string
  row_count: number
  column_count: number
  duplicate_row_count: number
  columns: ColumnProfile[]
  numeric_summary: NumericSummary[]
  numeric_distributions: NumericDistribution[]
  categorical_frequencies: CategoricalFrequency[]
  correlation: CorrelationMatrix | null
}

export async function getDatasetProfile(
  datasetId: string,
  signal?: AbortSignal,
): Promise<DatasetProfile> {
  const response = await fetch(`${API_BASE_URL}/api/datasets/${datasetId}/profile`, { signal })

  if (!response.ok) {
    const detail = await extractErrorDetail(response)
    throw new ApiError(detail, response.status)
  }

  return (await response.json()) as DatasetProfile
}

export function getEdaReportUrl(datasetId: string): string {
  return `${API_BASE_URL}/api/datasets/${datasetId}/profile/report`
}

async function extractErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) return body.detail
  } catch {
    // response body wasn't JSON; fall through to the generic message below
  }
  return `Request failed with status ${response.status}.`
}

export type TaskType = 'regression' | 'classification' | 'clustering'
export type ScalerType = 'none' | 'standard' | 'minmax'

export interface PreprocessingRequest {
  task: TaskType
  target: string | null
  features: string[]
  drop_duplicates: boolean
  scaler: ScalerType
}

export interface PreprocessingPreview {
  dataset_id: string
  task: TaskType
  target: string | null
  features: string[]
  original_rows: number
  removed_missing_rows: number
  removed_duplicate_rows: number
  final_rows: number
  final_feature_columns: string[]
  ready_to_train: boolean
  warnings: string[]
}

export async function getPreprocessingPreview(
  datasetId: string,
  request: PreprocessingRequest,
  signal?: AbortSignal,
): Promise<PreprocessingPreview> {
  const response = await fetch(`${API_BASE_URL}/api/datasets/${datasetId}/preprocessing-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    const detail = await extractErrorDetail(response)
    throw new ApiError(detail, response.status)
  }

  return (await response.json()) as PreprocessingPreview
}

export interface FeatureImportance {
  feature: string
  importance: number
}

export interface ActualVsPredictedPoint {
  actual: number
  predicted: number
}

export interface ResidualPoint {
  predicted: number
  residual: number
}

export interface RegressionCharts {
  actual_vs_predicted: ActualVsPredictedPoint[]
  residuals: ResidualPoint[]
}

export interface ConfusionMatrix {
  labels: string[]
  matrix: number[][]
}

export interface ClassificationCharts {
  confusion_matrix: ConfusionMatrix
}

export interface PcaPoint {
  x: number
  y: number
  cluster: string
}

export interface ClusterSizePoint {
  cluster: string
  size: number
}

export interface ClusteringCharts {
  pca_projection: PcaPoint[]
  cluster_sizes: ClusterSizePoint[]
}

export type ModelCharts = RegressionCharts | ClassificationCharts | ClusteringCharts

export interface ModelResult {
  key: string
  display_name: string
  status: 'success' | 'failed'
  duration_seconds: number
  best_params: Record<string, unknown> | null
  metrics: Record<string, number> | null
  warning: string | null
  feature_importances: FeatureImportance[] | null
  charts: ModelCharts | null
}

export function isClassificationCharts(charts: ModelCharts): charts is ClassificationCharts {
  return 'confusion_matrix' in charts
}

export function isClusteringCharts(charts: ModelCharts): charts is ClusteringCharts {
  return 'pca_projection' in charts
}

export interface TrainingResponse {
  dataset_id: string
  task: TaskType
  target: string | null
  train_rows: number
  test_rows: number
  primary_metric: string
  results: ModelResult[]
  winner_key: string | null
  experiment_id: string | null
}

export function getModelDownloadUrl(experimentId: string, modelKey: string): string {
  return `${API_BASE_URL}/api/experiments/${experimentId}/models/${modelKey}/download`
}

export function getExperimentDownloadUrl(experimentId: string): string {
  return `${API_BASE_URL}/api/experiments/${experimentId}/download`
}

export async function startTraining(
  datasetId: string,
  request: PreprocessingRequest,
  signal?: AbortSignal,
): Promise<TrainingResponse> {
  const response = await fetch(`${API_BASE_URL}/api/datasets/${datasetId}/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    const detail = await extractErrorDetail(response)
    throw new ApiError(detail, response.status)
  }

  return (await response.json()) as TrainingResponse
}
