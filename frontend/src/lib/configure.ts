import type { ColumnInfo, TaskType } from '@/lib/api'

// Matches the backend's CATEGORICAL_SKIP_UNIQUE_RATIO (dataset_profile.py):
// a categorical column with more than half distinct values is identifier-
// or free-text-like (e.g. customer_id), not a genuine category. Selecting
// one as a default feature would one-hot encode it into one column per row
// — excluded from the default selection for the same reason it's excluded
// from EDA frequency charts, though the user can still add it back by hand.
const HIGH_CARDINALITY_UNIQUE_RATIO = 0.5

function isIdentifierLike(column: ColumnInfo, rowCount: number): boolean {
  return (
    column.dtype === 'categorical' &&
    rowCount > 0 &&
    column.unique_count / rowCount > HIGH_CARDINALITY_UNIQUE_RATIO
  )
}

/**
 * All columns except the target (and identifier-like categorical columns)
 * are selected by default; for clustering (which has no target and v1 only
 * supports numeric features) the default is further narrowed to numeric
 * columns only.
 */
export function getDefaultFeatures(
  task: TaskType,
  columns: ColumnInfo[],
  target: string | null,
  rowCount: number,
): string[] {
  return columns
    .filter((column) => column.name !== target)
    .filter((column) => task !== 'clustering' || column.dtype === 'numeric')
    .filter((column) => !isIdentifierLike(column, rowCount))
    .map((column) => column.name)
}

export function isConfigComplete(
  task: TaskType,
  target: string | null,
  features: string[],
): boolean {
  if (features.length === 0) return false
  if (task !== 'clustering' && target === null) return false
  return true
}
