"""Utilitários de UI (ícones, cores, métricas)."""

from typing import Dict, List, Any
import plotly.express as px
import streamlit as st


def tipo_icon(tipo: str) -> str:
    icons: Dict[str, str] = {
        'História': '📗',
        'Debito Tecnico': '🔧',
        'Débito Técnico': '🔧',
        'Spike': '⚡',
        'Bug': '🐛',
        'Subtarefa': '📄',
        'Sub-task': '📄',
        'Task': '✅',
        'Task-DevSecOps': '✅',
        'Task-QA': '✅',
        'Impedimento': '🚫',
        'Epic': '🎯',
        'Initiative': '💎',
        'Story': '📗',
        'Technical Debt': '🔧',
    }
    return icons.get(tipo, '📋')


def status_color(status: str) -> str:
    colors: Dict[str, str] = {
        'Concluído': '#14892c', 'Done': '#14892c', 'Fechado': '#14892c', 'Finalizado': '#14892c', 'Resolvido': '#14892c',
        'Em Progresso': '#0052cc', 'In Progress': '#0052cc', 'Fazendo': '#0052cc', 'Desenvolvimento': '#0052cc',
        'A Fazer': '#ddd', 'To Do': '#ddd', 'Backlog': '#ddd', 'Novo': '#ddd',
        'Impedimento': '#de350b', 'Bloqueado': '#de350b', 'Blocked': '#de350b',
        'Cancelado': '#6b778c', 'Cancelled': '#6b778c',
    }
    return colors.get(status, '#8993a4')


def status_bar_figure(status_counts: Dict[str, int]):
    """Cria um gráfico de barras (Plotly) para distribuição por status com cores padronizadas."""
    if not status_counts:
        return px.bar(x=[], y=[])
    statuses = list(status_counts.keys())
    values = list(status_counts.values())
    return px.bar(
        x=statuses,
        y=values,
        title="Distribuição por Status",
        color=statuses,
        color_discrete_map={s: status_color(s) for s in statuses}
    )


def bar(df, x, y, title: str | None = None, color=None, color_map: Dict[str, str] | None = None):
    return px.bar(
        df, x=x, y=y, title=title or "",
        color=color,
        color_discrete_map=color_map or {}
    )


def pie(values, names, title: str | None = None, color_sequence=None):
    return px.pie(values=values, names=names, title=title or "", color_discrete_sequence=color_sequence)


def build_column_config(columns: List[str]) -> Dict[str, Any]:
    """Gera configuração de colunas padrão para dataframes exibidos no app.

    Detecta nomes conhecidos e aplica tamanhos/labels consistentes.
    """
    config: Dict[str, st.column_config.BaseColumn] = {}
    for col in columns:
        key = col
        name_upper = col.lower()

        if col == 'Chave':
            config[key] = st.column_config.TextColumn('Chave', width='small')
        elif col in ('Tipo', 'Tipo de Item'):
            label = 'Tipo' if col == 'Tipo' else 'Tipo de Item'
            config[key] = st.column_config.TextColumn(label, width='small')
        elif col == 'Resumo':
            config[key] = st.column_config.TextColumn('Resumo', width='large')
        elif col == 'Status':
            config[key] = st.column_config.TextColumn('Status', width='medium')
        elif col == 'Responsável':
            config[key] = st.column_config.TextColumn('Responsável', width='medium')
        elif col in ('Dias para Resolução', 'Dias Para Resolução'):
            config[key] = st.column_config.NumberColumn('Dias', width='small', format='%.0f')
        elif col == 'Tempo Total (dias)':
            config[key] = st.column_config.NumberColumn('Tempo Total (dias)', width='small')
        elif col == 'SP':
            config[key] = st.column_config.NumberColumn('SP', width='small')
        elif col == 'Story Points':
            config[key] = st.column_config.NumberColumn('SP', width='small')
        elif col == 'Tipo' and 'Item' in key:
            # fallback para nomes similares
            config[key] = st.column_config.TextColumn('Tipo', width='small')
        elif col == 'Sprint ID':
            config[key] = st.column_config.NumberColumn('Sprint', width='small')
        elif col == 'Sprint Nome':
            config[key] = st.column_config.TextColumn('Sprint', width='medium')
        elif col == 'Quantidade':
            config[key] = st.column_config.NumberColumn('Quantidade', width='small')
        elif col == 'Percentual':
            config[key] = st.column_config.TextColumn('Percentual', width='small')
        elif col == 'Total Issues' or name_upper == 'total_itens':
            config[key] = st.column_config.NumberColumn('Total', width='small')
        # Não configurar colunas desconhecidas; Streamlit aplica padrão

    return config


def metric(label: str, value, delta: str | None = None, help_text: str | None = None):
    st.metric(label=label, value=value, delta=delta, help=help_text)


def pct_delta(numerator: float, denominator: float) -> str:
    if denominator and denominator != 0:
        return f"{(numerator / denominator * 100):.1f}%"
    return "0.0%"


