"""Funções auxiliares para datas e cálculos de tempo."""
import pandas as pd


def to_datetime_safe(value):
    """Converte para Timestamp pandas, retornando NaT quando inválido."""
    try:
        return pd.to_datetime(value)
    except Exception:
        return pd.NaT


def compute_days_resolution(df: pd.DataFrame, created_col: str, resolved_col: str, out_col: str = 'Dias para Resolução') -> pd.DataFrame:
    """Calcula dias entre resolved e created quando ambos existem.

    Modifica o DataFrame em-place e retorna o próprio df.
    """
    if out_col not in df.columns:
        df[out_col] = None
    mask = df[created_col].notna() & df[resolved_col].notna()
    if mask.any():
        df.loc[mask, out_col] = (df.loc[mask, resolved_col] - df.loc[mask, created_col]).dt.days
    return df


