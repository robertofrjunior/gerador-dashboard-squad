"""
Componentes reutilizáveis de filtros para Streamlit.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date


class FilterComponents:
    """Componentes de filtros padronizados."""
    
    @staticmethod
    def tipo_item_filter(
        df: pd.DataFrame,
        key_suffix: str = "",
        include_all_option: bool = True,
        default_all: bool = True
    ) -> List[str]:
        """
        Filtro multi-select para Tipo de Item.
        
        Args:
            df: DataFrame com dados
            key_suffix: Sufixo para chave única do componente
            include_all_option: Se inclui opção "Todos"
            default_all: Se começa com "Todos" selecionado
            
        Returns:
            Lista de tipos selecionados
        """
        if 'Tipo de Item' not in df.columns or df.empty:
            return []
            
        tipos_disponiveis = ['Todos'] if include_all_option else []
        tipos_disponiveis.extend(sorted(df['Tipo de Item'].dropna().unique().tolist()))
        
        default_value = ['Todos'] if (include_all_option and default_all) else []
        
        return st.multiselect(
            "Filtrar por Tipo de Item",
            options=tipos_disponiveis,
            default=default_value,
            key=f"filter_tipo_item_{key_suffix}",
            help="Selecione os tipos de item para filtrar"
        )
    
    @staticmethod
    def sprint_filter(
        df: pd.DataFrame,
        key_suffix: str = "",
        include_all_option: bool = True
    ) -> List[str]:
        """
        Filtro multi-select para Sprint.
        
        Args:
            df: DataFrame com dados
            key_suffix: Sufixo para chave única
            include_all_option: Se inclui opção "Todas"
            
        Returns:
            Lista de sprints selecionadas
        """
        if 'Sprint ID' not in df.columns or df.empty:
            return []
            
        sprints_disponiveis = ['Todas'] if include_all_option else []
        sprints_disponiveis.extend(sorted(df['Sprint ID'].dropna().unique().tolist()))
        
        return st.multiselect(
            "Filtrar por Sprint",
            options=sprints_disponiveis,
            default=['Todas'] if include_all_option else [],
            key=f"filter_sprint_{key_suffix}",
            help="Selecione as sprints para filtrar"
        )
    
    @staticmethod
    def date_range_filter(
        df: pd.DataFrame,
        date_column: str,
        key_suffix: str = "",
        label_prefix: str = "Data"
    ) -> Tuple[Optional[date], Optional[date]]:
        """
        Filtro de intervalo de datas.
        
        Args:
            df: DataFrame com dados
            date_column: Nome da coluna de data
            key_suffix: Sufixo para chave única
            label_prefix: Prefixo para o label
            
        Returns:
            Tupla (data_inicio, data_fim)
        """
        if date_column not in df.columns or df.empty:
            return None, None
            
        date_series = pd.to_datetime(df[date_column], errors='coerce').dropna()
        
        if date_series.empty:
            return None, None
            
        min_date = date_series.min().date()
        max_date = date_series.max().date()
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                f"{label_prefix} - A partir de:",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key=f"filter_date_start_{key_suffix}",
                help=f"Filtrar itens a partir desta {label_prefix.lower()}"
            )
        
        with col2:
            end_date = st.date_input(
                f"{label_prefix} - Até:",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key=f"filter_date_end_{key_suffix}",
                help=f"Filtrar itens até esta {label_prefix.lower()}"
            )
        
        return start_date, end_date
    
    @staticmethod
    def column_selector(
        df: pd.DataFrame,
        default_columns: List[str],
        key_suffix: str = "",
        exclude_columns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Seletor de colunas para exibição.
        
        Args:
            df: DataFrame com dados
            default_columns: Colunas padrão selecionadas
            key_suffix: Sufixo para chave única
            exclude_columns: Colunas a excluir da lista
            
        Returns:
            Lista de colunas selecionadas
        """
        if df.empty:
            return []
            
        exclude_columns = exclude_columns or []
        available_columns = [col for col in df.columns if col not in exclude_columns]
        
        # Filtrar colunas padrão que existem
        valid_defaults = [col for col in default_columns if col in available_columns]
        
        return st.multiselect(
            "Selecione as colunas para exibir",
            options=available_columns,
            default=valid_defaults,
            key=f"column_selector_{key_suffix}",
            help="Escolha quais colunas mostrar na tabela"
        )


def apply_filters(
    df: pd.DataFrame,
    tipo_filter: List[str],
    sprint_filter: Optional[List[str]] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    date_column: str = 'Data Criação'
) -> pd.DataFrame:
    """
    Aplica múltiplos filtros ao DataFrame.
    
    Args:
        df: DataFrame original
        tipo_filter: Filtros de tipo de item
        sprint_filter: Filtros de sprint (opcional)
        date_start: Data de início (opcional)
        date_end: Data de fim (opcional)
        date_column: Nome da coluna de data
        
    Returns:
        DataFrame filtrado
    """
    filtered_df = df.copy()
    
    # Filtro por tipo
    if tipo_filter and 'Todos' not in tipo_filter and 'Tipo de Item' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Tipo de Item'].isin(tipo_filter)]
    
    # Filtro por sprint
    if (sprint_filter and 'Todas' not in sprint_filter and 
        'Sprint ID' in filtered_df.columns):
        filtered_df = filtered_df[filtered_df['Sprint ID'].isin(sprint_filter)]
    
    # Filtro por data
    if date_start and date_column in filtered_df.columns:
        date_series = pd.to_datetime(filtered_df[date_column], errors='coerce')
        filtered_df = filtered_df[date_series.dt.date >= date_start]
    
    if date_end and date_column in filtered_df.columns:
        date_series = pd.to_datetime(filtered_df[date_column], errors='coerce')
        filtered_df = filtered_df[date_series.dt.date <= date_end]
    
    return filtered_df


def show_filter_summary(
    original_count: int,
    filtered_count: int,
    filters_applied: List[str]
) -> None:
    """
    Mostra resumo dos filtros aplicados.
    
    Args:
        original_count: Número original de itens
        filtered_count: Número de itens após filtros
        filters_applied: Lista de filtros aplicados
    """
    percentage = (filtered_count / original_count * 100) if original_count > 0 else 0
    
    st.info(
        f"📊 Exibindo {filtered_count} de {original_count} itens ({percentage:.1f}%)"
        + (f" | Filtros: {', '.join(filters_applied)}" if filters_applied else "")
    )