from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    dtype: str  # "numeric" | "categorical"
    pandas_dtype: str
    missing_count: int
    missing_percentage: float
    unique_count: int


class NumericSummary(BaseModel):
    column: str
    count: int
    mean: float
    std: float | None
    min: float
    q25: float
    median: float
    q75: float
    max: float


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class NumericDistribution(BaseModel):
    column: str
    bins: list[HistogramBin]


class CategoryCount(BaseModel):
    value: str
    count: int


class CategoricalFrequency(BaseModel):
    column: str
    categories: list[CategoryCount]
    truncated: bool


class CorrelationMatrix(BaseModel):
    columns: list[str]
    matrix: list[list[float | None]]


class DatasetProfileResponse(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    duplicate_row_count: int
    columns: list[ColumnProfile]
    numeric_summary: list[NumericSummary]
    numeric_distributions: list[NumericDistribution]
    categorical_frequencies: list[CategoricalFrequency]
    correlation: CorrelationMatrix | None
