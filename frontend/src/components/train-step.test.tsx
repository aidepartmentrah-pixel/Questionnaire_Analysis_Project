import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TrainStep } from '@/components/train-step'
import * as api from '@/lib/api'
import type { DatasetSummary, PreprocessingRequest, TrainingResponse } from '@/lib/api'

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    startTraining: vi.fn(),
  }
})

const mockedStartTraining = vi.mocked(api.startTraining)

const DATASET: DatasetSummary = {
  dataset_id: 'abc123',
  filename: 'house_prices.csv',
  row_count: 222,
  column_count: 8,
  preview_row_count: 5,
  preview: [],
  columns: [],
}

const CONFIG: PreprocessingRequest = {
  task: 'regression',
  target: 'price_usd',
  features: ['area_m2', 'bedrooms'],
  drop_duplicates: true,
  scaler: 'standard',
}

function buildResponse(overrides: Partial<TrainingResponse> = {}): TrainingResponse {
  return {
    dataset_id: 'abc123',
    task: 'regression',
    target: 'price_usd',
    train_rows: 171,
    test_rows: 43,
    primary_metric: 'rmse',
    winner_key: 'linear_regression',
    experiment_id: 'exp123',
    results: [
      {
        key: 'linear_regression',
        display_name: 'Linear Regression',
        status: 'success',
        duration_seconds: 0.05,
        best_params: { fit_intercept: true },
        metrics: { mae: 100, rmse: 150, r2: 0.9 },
        warning: null,
        feature_importances: null,
        charts: {
          actual_vs_predicted: [{ actual: 100, predicted: 110 }],
          residuals: [{ predicted: 110, residual: -10 }],
        },
      },
      {
        key: 'random_forest_regressor',
        display_name: 'Random Forest Regressor',
        status: 'success',
        duration_seconds: 0.5,
        best_params: { n_estimators: 100 },
        metrics: { mae: 120, rmse: 180, r2: 0.85 },
        warning: null,
        feature_importances: [{ feature: 'area_m2', importance: 0.8 }],
        charts: {
          actual_vs_predicted: [{ actual: 100, predicted: 115 }],
          residuals: [{ predicted: 115, residual: -15 }],
        },
      },
      {
        key: 'xgboost_regressor',
        display_name: 'XGBoost Regressor',
        status: 'failed',
        duration_seconds: 0.2,
        best_params: null,
        metrics: null,
        warning: 'synthetic failure',
        feature_importances: null,
        charts: null,
      },
    ],
    ...overrides,
  }
}

describe('TrainStep', () => {
  beforeEach(() => {
    mockedStartTraining.mockReset()
  })

  it('prompts to finish configuration when no ready config is available', () => {
    render(<TrainStep dataset={DATASET} config={null} />)

    expect(screen.getByText(/finish a ready-to-train configuration/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /start training/i })).not.toBeInTheDocument()
  })

  it('shows the comparison table and highlights the winner after training', async () => {
    mockedStartTraining.mockResolvedValue(buildResponse())

    const user = userEvent.setup()
    render(<TrainStep dataset={DATASET} config={CONFIG} />)

    await user.click(screen.getByRole('button', { name: /start training/i }))

    expect(await screen.findByText('Model comparison')).toBeInTheDocument()
    expect(screen.getAllByText('Linear Regression')).not.toHaveLength(0)
    expect(screen.getByText('Best')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText(/best model: linear regression/i)).toBeInTheDocument()

    expect(mockedStartTraining).toHaveBeenCalledWith('abc123', CONFIG)
  })

  it('offers downloads for successful models, the best model, and the complete experiment, but not for a failed model', async () => {
    mockedStartTraining.mockResolvedValue(buildResponse())

    const user = userEvent.setup()
    render(<TrainStep dataset={DATASET} config={CONFIG} />)

    await user.click(screen.getByRole('button', { name: /start training/i }))
    await screen.findByText('Model comparison')

    expect(screen.getByRole('link', { name: /download complete experiment/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/experiments/exp123/download'),
    )

    expect(screen.getByRole('link', { name: /download best model/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/experiments/exp123/models/linear_regression/download'),
    )

    expect(screen.getByRole('link', { name: /download linear regression/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/experiments/exp123/models/linear_regression/download'),
    )
    expect(
      screen.getByRole('link', { name: /download random forest regressor/i }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /download xgboost regressor/i }),
    ).not.toBeInTheDocument()
  })

  it('shows a friendly error message when training fails', async () => {
    mockedStartTraining.mockRejectedValue(new api.ApiError('Only 10 usable rows remain.', 422))

    const user = userEvent.setup()
    render(<TrainStep dataset={DATASET} config={CONFIG} />)

    await user.click(screen.getByRole('button', { name: /start training/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Only 10 usable rows remain.')
  })

  it('shows classification metrics and a confusion matrix for a classification response', async () => {
    const classificationConfig: PreprocessingRequest = {
      task: 'classification',
      target: 'churned',
      features: ['age', 'annual_income'],
      drop_duplicates: true,
      scaler: 'standard',
    }

    mockedStartTraining.mockResolvedValue(
      buildResponse({
        task: 'classification',
        target: 'churned',
        primary_metric: 'f1',
        winner_key: 'random_forest_classifier',
        results: [
          {
            key: 'logistic_regression',
            display_name: 'Logistic Regression',
            status: 'success',
            duration_seconds: 0.05,
            best_params: { C: 1.0 },
            metrics: { accuracy: 0.8, precision: 0.79, recall: 0.8, f1: 0.795 },
            warning: null,
            feature_importances: null,
            charts: {
              confusion_matrix: {
                labels: ['0', '1'],
                matrix: [
                  [26, 2],
                  [5, 10],
                ],
              },
            },
          },
          {
            key: 'random_forest_classifier',
            display_name: 'Random Forest Classifier',
            status: 'success',
            duration_seconds: 0.5,
            best_params: { n_estimators: 100 },
            metrics: { accuracy: 0.84, precision: 0.83, recall: 0.84, f1: 0.832 },
            warning: null,
            feature_importances: [{ feature: 'age', importance: 0.6 }],
            charts: {
              confusion_matrix: {
                labels: ['0', '1'],
                matrix: [
                  [27, 1],
                  [4, 11],
                ],
              },
            },
          },
          {
            key: 'xgboost_classifier',
            display_name: 'XGBoost Classifier',
            status: 'success',
            duration_seconds: 0.6,
            best_params: { n_estimators: 50 },
            metrics: { accuracy: 0.84, precision: 0.83, recall: 0.84, f1: 0.832 },
            warning: null,
            feature_importances: [{ feature: 'age', importance: 0.55 }],
            charts: {
              confusion_matrix: {
                labels: ['0', '1'],
                matrix: [
                  [27, 1],
                  [4, 11],
                ],
              },
            },
          },
        ],
      }),
    )

    const user = userEvent.setup()
    render(<TrainStep dataset={DATASET} config={classificationConfig} />)

    await user.click(screen.getByRole('button', { name: /start training/i }))

    expect(await screen.findByText('Model comparison')).toBeInTheDocument()
    expect(screen.getByText('F1')).toBeInTheDocument()
    expect(screen.getByText('Accuracy')).toBeInTheDocument()
    expect(screen.queryByText('RMSE')).not.toBeInTheDocument()
    expect(screen.getByText(/best model: random forest classifier/i)).toBeInTheDocument()
    expect(screen.getByText('Confusion matrix')).toBeInTheDocument()
    expect(screen.getByText(/rows are actual classes/i)).toBeInTheDocument()
  })

  it('shows clustering metrics, PCA projection and cluster sizes for a clustering response', async () => {
    const clusteringConfig: PreprocessingRequest = {
      task: 'clustering',
      target: null,
      features: ['age', 'annual_income'],
      drop_duplicates: true,
      scaler: 'standard',
    }

    mockedStartTraining.mockResolvedValue(
      buildResponse({
        task: 'clustering',
        target: null,
        test_rows: 0,
        primary_metric: 'silhouette',
        winner_key: 'dbscan',
        results: [
          {
            key: 'kmeans',
            display_name: 'K-Means',
            status: 'success',
            duration_seconds: 0.2,
            best_params: { n_clusters: 3 },
            metrics: { silhouette: 0.58, davies_bouldin: 0.63, n_clusters: 3, noise_points: 0 },
            warning: null,
            feature_importances: null,
            charts: {
              pca_projection: [
                { x: 1, y: 1, cluster: '0' },
                { x: -1, y: -1, cluster: '1' },
              ],
              cluster_sizes: [
                { cluster: '0', size: 100 },
                { cluster: '1', size: 116 },
              ],
            },
          },
          {
            key: 'agglomerative_clustering',
            display_name: 'Agglomerative Clustering',
            status: 'success',
            duration_seconds: 0.15,
            best_params: { n_clusters: 3, linkage: 'ward' },
            metrics: { silhouette: 0.57, davies_bouldin: 0.65, n_clusters: 3, noise_points: 0 },
            warning: null,
            feature_importances: null,
            charts: {
              pca_projection: [{ x: 1, y: 1, cluster: '0' }],
              cluster_sizes: [{ cluster: '0', size: 216 }],
            },
          },
          {
            key: 'dbscan',
            display_name: 'DBSCAN',
            status: 'success',
            duration_seconds: 0.05,
            best_params: { eps: 0.5, min_samples: 5 },
            metrics: { silhouette: 0.65, davies_bouldin: 0.5, n_clusters: 3, noise_points: 51 },
            warning: null,
            feature_importances: null,
            charts: {
              pca_projection: [
                { x: 1, y: 1, cluster: '0' },
                { x: 0, y: 0, cluster: '-1' },
              ],
              cluster_sizes: [{ cluster: '0', size: 165 }],
            },
          },
        ],
      }),
    )

    const user = userEvent.setup()
    render(<TrainStep dataset={DATASET} config={clusteringConfig} />)

    await user.click(screen.getByRole('button', { name: /start training/i }))

    expect(await screen.findByText('Model comparison')).toBeInTheDocument()
    expect(screen.getByText('Silhouette')).toBeInTheDocument()
    expect(screen.getByText('Noise points')).toBeInTheDocument()
    expect(screen.queryByText('RMSE')).not.toBeInTheDocument()
    expect(screen.getByText(/best model: dbscan/i)).toBeInTheDocument()
    expect(screen.getByText('Cluster projection (PCA)')).toBeInTheDocument()
    expect(screen.getByText('Cluster sizes')).toBeInTheDocument()
    expect(screen.getByText(/marked as noise/i)).toBeInTheDocument()
  })
})
