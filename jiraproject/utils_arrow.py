"""Helpers para compatibilidade com Arrow/Streamlit."""
import pandas as pd
from typing import Iterable, Optional, List


def to_arrow_safe_numeric(df: pd.DataFrame, numeric_cols: Iterable[str]) -> pd.DataFrame:
    """Converte colunas para numérico coerce e mantém NaN (sem strings)."""
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def make_display_copy(
    df: pd.DataFrame,
    numeric_cols: Optional[Iterable[str]] = None,
    decimals: int = 1,
    nan_str: str = '—'
) -> pd.DataFrame:
    """Copia para exibição: arredonda numéricos e troca NaN por string, sem afetar df original."""
    d = df.copy()
    if numeric_cols is None:
        numeric_set = set(d.select_dtypes(include='number').columns)
    else:
        numeric_set = set([c for c in numeric_cols if c in d.columns])

    # Coerce and round numeric columns
    for col in numeric_set:
        d[col] = pd.to_numeric(d[col], errors='coerce')
        if decimals is not None:
            try:
                d[col] = d[col].round(decimals)
            except Exception:
                pass

    # Fill NaN on non-numeric columns with string marker
    non_numeric_cols = [c for c in d.columns if c not in numeric_set]
    if non_numeric_cols:
        d[non_numeric_cols] = d[non_numeric_cols].fillna(nan_str)

    # For display-only requirement in tests: replace NaN in numeric columns with marker too
    # to match expected output in UI contexts
    for col in numeric_set:
        # create a display series with NaN shown as marker but keep dtype float where possible
        if d[col].isna().any():
            d[col] = d[col].astype(object).where(d[col].notna(), nan_str)
    return d


