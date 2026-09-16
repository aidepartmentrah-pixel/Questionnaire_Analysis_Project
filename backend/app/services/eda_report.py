"""Self-contained downloadable HTML EDA report.

Pure HTML with inline CSS and no JavaScript or external assets (fonts,
scripts, images) so the file opens correctly from disk indefinitely, with
no network dependency.
"""

from __future__ import annotations

import html as html_lib
from datetime import UTC, datetime

from app.schemas.profile import DatasetProfileResponse

_STYLE = """
  body {
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    color: #0f172a;
    background: #f8fafc;
    margin: 0;
    padding: 2rem;
  }
  h1 { font-size: 1.375rem; margin-bottom: 0.25rem; }
  .meta { color: #64748b; font-size: 0.875rem; margin-bottom: 1.5rem; }
  .cards { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
  .card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    min-width: 140px;
  }
  .card .value { font-size: 1.25rem; font-weight: 600; }
  .card .label { font-size: 0.75rem; color: #64748b; }
  section { margin-bottom: 2rem; }
  h2 { font-size: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; }
  h3 { font-size: 0.875rem; margin-bottom: 0.5rem; }
  table { border-collapse: collapse; width: 100%; font-size: 0.8125rem; background: #fff; }
  th, td { border: 1px solid #e2e8f0; padding: 0.375rem 0.625rem; text-align: left; }
  th { background: #f1f5f9; }
  .bar-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0; }
  .bar-label {
    width: 160px;
    font-size: 0.75rem;
    color: #334155;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .bar-track { flex: 1; background: #f1f5f9; border-radius: 4px; height: 14px; overflow: hidden; }
  .bar-fill { background: #2563eb; height: 100%; }
  .bar-count { width: 48px; text-align: right; font-size: 0.75rem; color: #64748b; }
"""


def _esc(value: object) -> str:
    return html_lib.escape(str(value))


def _overview_cards(profile: DatasetProfileResponse) -> str:
    cards = [
        ("Rows", f"{profile.row_count:,}"),
        ("Columns", str(profile.column_count)),
        ("Duplicate rows", str(profile.duplicate_row_count)),
    ]
    return "".join(
        f'<div class="card"><div class="value">{_esc(value)}</div>'
        f'<div class="label">{_esc(label)}</div></div>'
        for label, value in cards
    )


def _columns_table(profile: DatasetProfileResponse) -> str:
    rows = "".join(
        f"<tr><td>{_esc(c.name)}</td><td>{_esc(c.dtype)}</td><td>{_esc(c.pandas_dtype)}</td>"
        f"<td>{c.missing_count}</td><td>{c.missing_percentage:.2f}%</td><td>{c.unique_count}</td></tr>"
        for c in profile.columns
    )
    return (
        "<table><thead><tr><th>Column</th><th>Type</th><th>Pandas dtype</th>"
        "<th>Missing</th><th>Missing %</th><th>Unique</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _numeric_summary_table(profile: DatasetProfileResponse) -> str:
    if not profile.numeric_summary:
        return "<p>No numeric columns.</p>"
    rows = "".join(
        f"<tr><td>{_esc(s.column)}</td><td>{s.count}</td><td>{s.mean:.2f}</td>"
        f"<td>{'' if s.std is None else f'{s.std:.2f}'}</td><td>{s.min:.2f}</td>"
        f"<td>{s.q25:.2f}</td><td>{s.median:.2f}</td><td>{s.q75:.2f}</td><td>{s.max:.2f}</td></tr>"
        for s in profile.numeric_summary
    )
    return (
        "<table><thead><tr><th>Column</th><th>Count</th><th>Mean</th><th>Std</th>"
        "<th>Min</th><th>25%</th><th>Median</th><th>75%</th><th>Max</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _bar_rows(items: list[tuple[str, int]]) -> str:
    max_count = max((count for _, count in items), default=0) or 1

    def _row(label: str, count: int) -> str:
        pct = round(count / max_count * 100, 1)
        return (
            f'<div class="bar-row"><div class="bar-label" title="{label}">{label}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<div class="bar-count">{count}</div></div>'
        )

    return "".join(_row(label, count) for label, count in items)


def _format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _format_bin_label(bin_start: float, bin_end: float) -> str:
    if bin_start == bin_end:
        return _format_number(bin_start)
    return f"{_format_number(bin_start)}–{_format_number(bin_end)}"


def _numeric_distributions_section(profile: DatasetProfileResponse) -> str:
    if not profile.numeric_distributions:
        return "<p>No numeric distributions available.</p>"
    blocks = []
    for dist in profile.numeric_distributions:
        items = [(_esc(_format_bin_label(b.bin_start, b.bin_end)), b.count) for b in dist.bins]
        blocks.append(f"<h3>{_esc(dist.column)}</h3>{_bar_rows(items)}")
    return "".join(blocks)


def _categorical_frequencies_section(profile: DatasetProfileResponse) -> str:
    if not profile.categorical_frequencies:
        return "<p>No categorical columns with a suitable number of categories.</p>"
    blocks = []
    for freq in profile.categorical_frequencies:
        items = [(_esc(c.value), c.count) for c in freq.categories]
        note = " (top categories, remainder grouped as “Other”)" if freq.truncated else ""
        blocks.append(f"<h3>{_esc(freq.column)}{note}</h3>{_bar_rows(items)}")
    return "".join(blocks)


def _correlation_section(profile: DatasetProfileResponse) -> str:
    if profile.correlation is None:
        return "<p>Not enough numeric columns for a correlation matrix.</p>"

    columns = profile.correlation.columns
    header = "".join(f"<th>{_esc(c)}</th>" for c in columns)
    rows = []
    for row_label, row_values in zip(columns, profile.correlation.matrix, strict=True):
        cells = []
        for value in row_values:
            if value is None:
                cells.append("<td>—</td>")
            else:
                intensity = min(1.0, abs(value))
                color = f"rgba(37, 99, 235, {intensity:.2f})"
                text_color = "#fff" if intensity > 0.55 else "#0f172a"
                cells.append(f'<td style="background:{color};color:{text_color}">{value:.2f}</td>')
        rows.append(f"<tr><th>{_esc(row_label)}</th>{''.join(cells)}</tr>")

    return f"<table><thead><tr><th></th>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def render_eda_report_html(profile: DatasetProfileResponse) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>EDA Report – {_esc(profile.filename)}</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>Exploratory Data Analysis</h1>
<p class="meta">{_esc(profile.filename)} &middot; generated {generated_at}</p>

<div class="cards">{_overview_cards(profile)}</div>

<section>
<h2>Columns</h2>
{_columns_table(profile)}
</section>

<section>
<h2>Numeric summary</h2>
{_numeric_summary_table(profile)}
</section>

<section>
<h2>Numeric distributions</h2>
{_numeric_distributions_section(profile)}
</section>

<section>
<h2>Categorical frequencies</h2>
{_categorical_frequencies_section(profile)}
</section>

<section>
<h2>Correlation matrix</h2>
{_correlation_section(profile)}
</section>
</body>
</html>
"""
