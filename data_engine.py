"""
data_engine.py
================
Core data processing module for DataSense AI.
Performs real Pandas calculations for data ingestion, quality checks,
statistical summaries, feature classification, and smart header row detection.
"""

from typing import Tuple, Dict, Any, List, Optional
import io
import pandas as pd


def _reset_file_pointer(file_source: Any) -> None:
    """Helper to reset file pointer if the source is a file-like object."""
    if hasattr(file_source, "seek"):
        try:
            file_source.seek(0)
        except Exception:
            pass


def detect_header_row(file_source: Any, max_check_rows: int = 6) -> int:
    """
    Scans the first few rows of an Excel or CSV file to identify the most likely
    header row. Detects:
    1. Blank or metadata title rows (e.g., 'Annual Report 2024' with only 1 filled cell).
    2. Rows where almost all cells are NaN.
    3. Finds the row with the most complete set of distinct column names.

    Returns:
        0-based index of the detected header row (defaults to 0).
    """
    _reset_file_pointer(file_source)
    try:
        filename = getattr(file_source, "name", str(file_source)).lower()
        if filename.endswith(".csv"):
            raw_sample = pd.read_csv(file_source, header=None, nrows=max_check_rows)
        elif filename.endswith((".xlsx", ".xls")):
            raw_sample = pd.read_excel(file_source, header=None, nrows=max_check_rows)
        else:
            return 0
    except Exception:
        return 0
    finally:
        _reset_file_pointer(file_source)

    if raw_sample.empty:
        return 0

    total_cols = raw_sample.shape[1]
    best_row_idx = 0
    max_score = -1.0

    for idx, row in raw_sample.iterrows():
        # Clean non-null, non-empty values
        non_null_vals = [
            str(v).strip() for v in row 
            if pd.notna(v) and str(v).strip() != "" and str(v).lower() != "nan"
        ]
        num_non_null = len(non_null_vals)

        # Skip completely blank rows
        if num_non_null == 0:
            continue

        # If a row has only 1 non-null value but total_cols > 2, it is almost certainly a title banner row
        if num_non_null == 1 and total_cols > 2:
            continue

        # Check uniqueness of candidate column names
        unique_vals = set(non_null_vals)
        unique_ratio = len(unique_vals) / num_non_null if num_non_null > 0 else 0

        # Score balances count of non-null headers and their uniqueness
        score = (num_non_null * 2.0) + (unique_ratio * 3.0)

        # Only replace if strictly higher score (favor earlier rows on tie)
        if score > max_score:
            max_score = score
            best_row_idx = int(idx)

    return best_row_idx


def check_unnamed_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Checks if DataFrame columns contain 'Unnamed:' or blank column names.
    Returns:
        (has_unnamed, list_of_unnamed_columns)
    """
    unnamed = [
        str(c) for c in df.columns 
        if str(c).startswith("Unnamed:") or str(c).strip() == "" or str(c).lower() == "nan"
    ]
    return (len(unnamed) > 0), unnamed


def optimize_column_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures columns are correctly cast to numeric, datetime, or categorical types.
    Crucial after header row adjustments where Excel or Pandas may have loaded
    numeric columns as 'object' strings because of earlier banner rows.
    """
    df = df.copy()

    # Clean column names (strip whitespace and ensure valid names)
    clean_cols = []
    for i, c in enumerate(df.columns):
        if pd.isna(c) or str(c).strip() == "":
            clean_cols.append(f"Column_{i+1}")
        else:
            clean_cols.append(str(c).strip())
    df.columns = clean_cols

    for col in df.columns:
        series = df[col]

        # Skip if already recognized as numeric or boolean
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            continue

        valid_series = series.dropna()
        if valid_series.empty:
            continue

        # 1. Try numeric conversion
        try:
            num_series = pd.to_numeric(series, errors="coerce")
            valid_numeric_count = num_series.dropna().count()
            # If >= 70% of non-null rows convert cleanly into numbers
            if valid_numeric_count > 0 and (valid_numeric_count / len(valid_series)) >= 0.70:
                df[col] = num_series
                continue
        except Exception:
            pass

        # 2. Try datetime conversion (if strings look like formatted dates)
        try:
            if series.dtype == "object":
                sample_val = str(valid_series.iloc[0]).strip()
                if any(sep in sample_val for sep in ["-", "/", ":"]) and len(sample_val) >= 6:
                    dt_series = pd.to_datetime(series, errors="coerce")
                    valid_dt_count = dt_series.dropna().count()
                    if valid_dt_count > 0 and (valid_dt_count / len(valid_series)) >= 0.70:
                        df[col] = dt_series
                        continue
        except Exception:
            pass

    return df


def load_dataset(file_source: Any, header_row: Optional[int] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Loads a dataset from an uploaded file object or a local file path.
    Supports CSV (.csv) and Excel (.xlsx, .xls) formats.
    Automatically detects or uses the specified header row and optimizes data types.

    Returns:
        (df, None) if successful, or (None, error_message) if failed.
    """
    _reset_file_pointer(file_source)

    try:
        # Auto-detect header row if not explicitly provided
        effective_header = header_row if header_row is not None else detect_header_row(file_source)

        filename = getattr(file_source, "name", str(file_source)).lower()

        if filename.endswith(".csv"):
            df = pd.read_csv(file_source, header=effective_header)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_source, header=effective_header)
        else:
            return None, f"Unsupported file extension: {filename}. Please upload .csv or .xlsx."

        if df.empty:
            return None, "The uploaded file is empty. Please provide a valid dataset."

        # Automatically clean column types and names
        df = optimize_column_types(df)

        # Store effective header row in dataframe metadata
        df.attrs["header_row"] = effective_header

        return df, None

    except Exception as e:
        return None, f"Error reading file: {str(e)}"
    finally:
        _reset_file_pointer(file_source)


def get_dataset_overview(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates high-level metadata and quality metrics for the dataset.
    All numbers are computed directly with Pandas.
    """
    total_rows = int(df.shape[0])
    total_cols = int(df.shape[1])
    total_missing = int(df.isnull().sum().sum())
    total_duplicates = int(df.duplicated().sum())

    # Calculate memory footprint in KB or MB
    memory_bytes = df.memory_usage(deep=True).sum()
    if memory_bytes > 1024 * 1024:
        memory_str = f"{memory_bytes / (1024 * 1024):.2f} MB"
    else:
        memory_str = f"{memory_bytes / 1024:.2f} KB"

    # Separate column types accurately
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool", "string"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    has_unnamed, unnamed_cols = check_unnamed_columns(df)

    return {
        "rows": total_rows,
        "cols": total_cols,
        "missing_cells": total_missing,
        "duplicate_rows": total_duplicates,
        "memory": memory_str,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "datetime_cols": datetime_cols,
        "has_unnamed": has_unnamed,
        "unnamed_cols": unnamed_cols,
        "header_row": df.attrs.get("header_row", 0),
    }


def get_missing_values_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates a column-level breakdown of missing values.
    """
    missing_count = df.isnull().sum()
    missing_pct = (missing_count / len(df)) * 100

    report = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Count": missing_count.values,
        "Missing Percentage (%)": missing_pct.round(2).values,
    })

    # Sort descending by missing count
    return report.sort_values(by="Missing Count", ascending=False).reset_index(drop=True)


def get_duplicate_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns all rows that are identified as duplicate records.
    """
    return df[df.duplicated(keep=False)].copy()


def get_statistical_summary(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Computes genuine statistical metrics (mean, std, min, quartiles, max)
    for all numeric columns.
    """
    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        return None
    
    # Transpose so columns are metrics and rows are features
    summary = numeric_df.describe().T
    summary = summary.rename(columns={
        "count": "Count",
        "mean": "Mean",
        "std": "Std Dev",
        "min": "Min",
        "25%": "25% (Q1)",
        "50%": "50% (Median)",
        "75%": "75% (Q3)",
        "max": "Max"
    })
    return summary.round(2)


def generate_data_context_for_ai(df: pd.DataFrame) -> str:
    """
    Constructs a factual, strictly-computed text summary of the dataset.
    This context is supplied to Gemini so it explains real data without hallucinating.
    """
    overview = get_dataset_overview(df)
    missing_report = get_missing_values_report(df)
    stats_summary = get_statistical_summary(df)

    # Missing columns summary
    missing_cols = missing_report[missing_report["Missing Count"] > 0]
    missing_text = ""
    if not missing_cols.empty:
        for _, row in missing_cols.iterrows():
            missing_text += f"- {row['Column Name']}: {row['Missing Count']} missing ({row['Missing Percentage (%)']}%)\n"
    else:
        missing_text = "No missing values found across any columns."

    # Numeric statistics summary
    stats_text = ""
    if stats_summary is not None:
        stats_text = stats_summary.to_string()
    else:
        stats_text = "No numeric columns available for statistical summary."

    # Sample rows (first 5 rows)
    try:
        sample_text = df.head(5).to_string(index=False)
    except Exception:
        sample_text = str(df.head(5))

    context = f"""=== DATASET FACTS & REAL PANDAS CALCULATIONS ===
- Shape: {overview['rows']} rows, {overview['cols']} columns
- Total Missing Values: {overview['missing_cells']} cells
- Total Duplicate Rows: {overview['duplicate_rows']} rows
- Memory Usage: {overview['memory']}
- Numeric Columns: {', '.join(overview['numeric_cols']) if overview['numeric_cols'] else 'None'}
- Categorical Columns: {', '.join(overview['categorical_cols']) if overview['categorical_cols'] else 'None'}

=== MISSING VALUES BREAKDOWN ===
{missing_text}

=== NUMERICAL STATISTICS (Calculated with df.describe()) ===
{stats_text}

=== FIRST 5 ROWS SAMPLE ===
{sample_text}
"""
    return context
