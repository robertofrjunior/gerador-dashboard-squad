"""
Utilitários para cálculos estatísticos e transformações de dados.
"""

import pandas as pd
from typing import Optional, List, Dict, Any
from .utils_dates import compute_days_resolution


def calc_resolution_days(
    df: pd.DataFrame, 
    created_col: str = 'Data Criação', 
    resolved_col: str = 'Data Resolução', 
    out_col: str = 'Dias para Resolução',
    ensure_numeric: bool = True
) -> pd.DataFrame:
    """
    Calcula dias para resolução de forma robusta.
    
    Args:
        df: DataFrame com dados
        created_col: Nome da coluna de criação
        resolved_col: Nome da coluna de resolução  
        out_col: Nome da coluna de saída
        ensure_numeric: Se True, garante que resultado é numérico
        
    Returns:
        DataFrame com coluna de dias calculada
    """
    if df.empty:
        df[out_col] = pd.Series(dtype='float64')
        return df
        
    result_df = compute_days_resolution(df, created_col, resolved_col, out_col=out_col)
    
    if ensure_numeric and out_col in result_df.columns:
        result_df[out_col] = pd.to_numeric(result_df[out_col], errors='coerce')
    
    return result_df


def get_resolved_items(df: pd.DataFrame, days_col: str = 'Dias para Resolução') -> pd.DataFrame:
    """
    Filtra apenas itens que foram resolvidos (têm dias para resolução).
    
    Args:
        df: DataFrame com dados
        days_col: Nome da coluna de dias
        
    Returns:
        DataFrame apenas com itens resolvidos
    """
    if days_col not in df.columns:
        return pd.DataFrame()
    
    return df[df[days_col].notna()].copy()


def calculate_time_statistics(
    df: pd.DataFrame, 
    days_col: str = 'Dias para Resolução'
) -> Dict[str, Optional[float]]:
    """
    Calcula estatísticas de tempo para itens resolvidos.
    
    Args:
        df: DataFrame com dados
        days_col: Nome da coluna de dias
        
    Returns:
        Dicionário com estatísticas (mean, median, p85, min, max, count)
    """
    resolved_df = get_resolved_items(df, days_col)
    
    if resolved_df.empty:
        return {
            'mean': None,
            'median': None,
            'p85': None,
            'min': None,
            'max': None,
            'count': 0
        }
    
    days_series = resolved_df[days_col]
    
    return {
        'mean': float(days_series.mean()),
        'median': float(days_series.median()),
        'p85': float(days_series.quantile(0.85)),
        'min': float(days_series.min()),
        'max': float(days_series.max()),
        'count': len(resolved_df)
    }


def group_by_time_stats(
    df: pd.DataFrame,
    group_col: str,
    days_col: str = 'Dias para Resolução',
    round_digits: int = 1
) -> pd.DataFrame:
    """
    Agrupa dados calculando estatísticas de tempo por grupo.
    
    Args:
        df: DataFrame com dados
        group_col: Coluna para agrupar
        days_col: Coluna de dias para resolução
        round_digits: Dígitos para arredondar
        
    Returns:
        DataFrame agrupado com estatísticas
    """
    resolved_df = get_resolved_items(df, days_col)
    
    if resolved_df.empty:
        return pd.DataFrame(columns=[group_col, 'Média Dias', 'Total Itens'])
    
    grouped = resolved_df.groupby(group_col)[days_col].agg(['mean', 'count']).reset_index()
    grouped.columns = [group_col, 'Média Dias', 'Total Itens']
    grouped['Média Dias'] = grouped['Média Dias'].round(round_digits)
    
    return grouped


def prepare_dataframe_for_display(
    df: pd.DataFrame,
    columns_to_keep: List[str],
    ensure_days_calculation: bool = True,
    days_col: str = 'Dias para Resolução'
) -> pd.DataFrame:
    """
    Prepara DataFrame para exibição com cálculo de dias se necessário.
    
    Args:
        df: DataFrame original
        columns_to_keep: Colunas para manter
        ensure_days_calculation: Se True, calcula dias para resolução
        days_col: Nome da coluna de dias
        
    Returns:
        DataFrame preparado para exibição
    """
    display_df = df.copy()
    
    if ensure_days_calculation and days_col in columns_to_keep:
        display_df = calc_resolution_days(display_df)
    
    # Filtrar apenas colunas que existem
    available_columns = [col for col in columns_to_keep if col in display_df.columns]
    
    return display_df[available_columns]