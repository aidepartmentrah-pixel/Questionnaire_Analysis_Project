import { describe, expect, it } from 'vitest'

import { getDefaultFeatures, isConfigComplete } from '@/lib/configure'
import type { ColumnInfo } from '@/lib/api'

const ROW_COUNT = 10

const COLUMNS: ColumnInfo[] = [
  { name: 'id', dtype: 'categorical', pandas_dtype: 'object', unique_count: 10 },
  { name: 'age', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 8 },
  { name: 'income', dtype: 'numeric', pandas_dtype: 'float64', unique_count: 10 },
  { name: 'region', dtype: 'categorical', pandas_dtype: 'object', unique_count: 3 },
  { name: 'target', dtype: 'numeric', pandas_dtype: 'int64', unique_count: 2 },
]

describe('getDefaultFeatures', () => {
  it('selects every column except the target and identifier-like columns for regression', () => {
    expect(getDefaultFeatures('regression', COLUMNS, 'target', ROW_COUNT)).toEqual([
      'age',
      'income',
      'region',
    ])
  })

  it('selects every column except the target and identifier-like columns for classification', () => {
    expect(getDefaultFeatures('classification', COLUMNS, 'target', ROW_COUNT)).toEqual([
      'age',
      'income',
      'region',
    ])
  })

  it('selects only numeric columns for clustering, with no target', () => {
    expect(getDefaultFeatures('clustering', COLUMNS, null, ROW_COUNT)).toEqual([
      'age',
      'income',
      'target',
    ])
  })

  it('excludes a fully-unique categorical column (e.g. a customer_id) even without a target', () => {
    expect(getDefaultFeatures('regression', COLUMNS, null, ROW_COUNT)).not.toContain('id')
  })

  it('keeps a low-cardinality categorical column even at 100% unique numeric columns', () => {
    expect(getDefaultFeatures('regression', COLUMNS, null, ROW_COUNT)).toContain('region')
  })
})

describe('isConfigComplete', () => {
  it('is incomplete with no features selected', () => {
    expect(isConfigComplete('regression', 'target', [])).toBe(false)
  })

  it('is incomplete for a supervised task with no target', () => {
    expect(isConfigComplete('classification', null, ['age'])).toBe(false)
  })

  it('is complete for a supervised task with a target and features', () => {
    expect(isConfigComplete('regression', 'target', ['age', 'income'])).toBe(true)
  })

  it('is complete for clustering with features and no target', () => {
    expect(isConfigComplete('clustering', null, ['age', 'income'])).toBe(true)
  })
})
