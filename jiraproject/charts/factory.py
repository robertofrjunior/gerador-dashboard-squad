"""
Factory pattern para criação padronizada de gráficos.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Union
from ..utils.ui import status_color


class ChartFactory:
    """Factory para criação de gráficos padronizados."""
    
    @staticmethod
    def create_pie_chart(
        values: List[Union[int, float]],
        names: List[str],
        title: str = "",
        color_sequence: Optional[List[str]] = None,
        hole: float = 0.0
    ) -> go.Figure:
        """
        Cria gráfico de pizza padronizado.
        
        Args:
            values: Valores para o gráfico
            names: Nomes das categorias
            title: Título do gráfico
            color_sequence: Sequência de cores personalizada
            hole: Tamanho do buraco (0.0 para pizza, >0 para donut)
            
        Returns:
            Figura plotly
        """
        fig = px.pie(
            values=values,
            names=names,
            title=title,
            color_discrete_sequence=color_sequence
        )
        
        if hole > 0:
            fig.update_traces(hole=hole)
        
        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5
            )
        )
        
        return fig
    
    @staticmethod
    def create_bar_chart(
        df: Optional[pd.DataFrame] = None,
        x: Optional[Union[str, List]] = None,
        y: Optional[Union[str, List]] = None,
        title: str = "",
        color: Optional[str] = None,
        color_map: Optional[Dict[str, str]] = None,
        horizontal: bool = False,
        show_values: bool = False
    ) -> go.Figure:
        """
        Cria gráfico de barras padronizado.
        
        Args:
            df: DataFrame com dados (opcional)
            x: Dados do eixo X ou nome da coluna
            y: Dados do eixo Y ou nome da coluna  
            title: Título do gráfico
            color: Coluna para colorir ou cor única
            color_map: Mapeamento de cores personalizado
            horizontal: Se True, cria barras horizontais
            show_values: Se True, mostra valores nas barras
            
        Returns:
            Figura plotly
        """
        if df is not None:
            # Usar dados do DataFrame
            if horizontal:
                fig = px.bar(df, x=y, y=x, title=title, color=color,
                           color_discrete_map=color_map, orientation='h')
            else:
                fig = px.bar(df, x=x, y=y, title=title, color=color,
                           color_discrete_map=color_map)
        else:
            # Usar dados diretos
            if horizontal:
                fig = go.Figure(data=[go.Bar(x=y, y=x, orientation='h')])
            else:
                fig = go.Figure(data=[go.Bar(x=x, y=y)])
            fig.update_layout(title=title)
        
        if show_values:
            fig.update_traces(texttemplate='%{y}', textposition='outside')
        
        fig.update_layout(
            xaxis_tickangle=-45 if not horizontal else 0,
            showlegend=False if not color else True
        )
        
        return fig
    
    @staticmethod
    def create_status_bar_chart(
        status_counts: Dict[str, int],
        title: str = "Distribuição por Status"
    ) -> go.Figure:
        """
        Cria gráfico de barras específico para status com cores do Jira.
        
        Args:
            status_counts: Dicionário com contagem por status
            title: Título do gráfico
            
        Returns:
            Figura plotly
        """
        if not status_counts:
            return go.Figure()
        
        statuses = list(status_counts.keys())
        counts = list(status_counts.values())
        colors = [status_color(status) for status in statuses]
        
        fig = go.Figure(data=[
            go.Bar(
                x=statuses,
                y=counts,
                marker_color=colors,
                text=counts,
                textposition='inside',
                textfont=dict(color='white', size=12)
            )
        ])
        
        fig.update_layout(
            title=title,
            xaxis_tickangle=-45,
            showlegend=False,
            yaxis_title="Quantidade de Itens"
        )
        
        return fig
    
    @staticmethod
    def create_scatter_plot(
        df: pd.DataFrame,
        x: str,
        y: str,
        color: Optional[str] = None,
        size: Optional[str] = None,
        hover_data: Optional[List[str]] = None,
        title: str = ""
    ) -> go.Figure:
        """
        Cria gráfico de dispersão padronizado.
        
        Args:
            df: DataFrame com dados
            x: Nome da coluna para eixo X
            y: Nome da coluna para eixo Y
            color: Nome da coluna para cores
            size: Nome da coluna para tamanhos
            hover_data: Colunas para mostrar no hover
            title: Título do gráfico
            
        Returns:
            Figura plotly
        """
        fig = px.scatter(
            df, x=x, y=y, color=color, size=size,
            hover_data=hover_data, title=title
        )
        
        fig.update_layout(
            xaxis_title=x,
            yaxis_title=y
        )
        
        return fig
    
    @staticmethod
    def create_histogram(
        df: pd.DataFrame,
        x: str,
        title: str = "",
        nbins: int = 20,
        color: Optional[str] = None
    ) -> go.Figure:
        """
        Cria histograma padronizado.
        
        Args:
            df: DataFrame com dados
            x: Nome da coluna para o histograma
            title: Título do gráfico
            nbins: Número de bins
            color: Cor das barras
            
        Returns:
            Figura plotly
        """
        fig = px.histogram(
            df, x=x, nbins=nbins, title=title,
            color_discrete_sequence=[color] if color else None
        )
        
        fig.update_layout(
            xaxis_title=x,
            yaxis_title="Frequência"
        )
        
        return fig
    
    @staticmethod
    def create_line_chart(
        df: pd.DataFrame,
        x: str,
        y: str,
        color: Optional[str] = None,
        title: str = "",
        markers: bool = True
    ) -> go.Figure:
        """
        Cria gráfico de linha padronizado.
        
        Args:
            df: DataFrame com dados
            x: Nome da coluna para eixo X
            y: Nome da coluna para eixo Y
            color: Nome da coluna para diferentes linhas
            title: Título do gráfico
            markers: Se True, mostra marcadores nos pontos
            
        Returns:
            Figura plotly
        """
        fig = px.line(
            df, x=x, y=y, color=color, title=title,
            markers=markers
        )
        
        fig.update_layout(
            xaxis_title=x,
            yaxis_title=y
        )
        
        return fig
    
    @staticmethod
    def create_burndown_chart(
        dates: List[str],
        ideal_line: List[float],
        actual_line: List[float],
        title: str = "Burndown Chart"
    ) -> go.Figure:
        """
        Cria gráfico burndown padronizado.
        
        Args:
            dates: Lista de datas
            ideal_line: Linha ideal de progresso
            actual_line: Linha real de progresso
            title: Título do gráfico
            
        Returns:
            Figura plotly
        """
        fig = go.Figure()
        
        # Linha ideal
        fig.add_trace(go.Scatter(
            x=dates,
            y=ideal_line,
            mode='lines',
            name='Ideal',
            line=dict(color='lightblue', dash='dash')
        ))
        
        # Linha real
        fig.add_trace(go.Scatter(
            x=dates,
            y=actual_line,
            mode='lines+markers',
            name='Real',
            line=dict(color='blue')
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Data",
            yaxis_title="Story Points Restantes",
            hovermode='x unified'
        )
        
        return fig


class ChartThemes:
    """Temas e configurações padrão para gráficos."""
    
    JIRA_COLORS = {
        'primary': '#0052CC',
        'secondary': '#36B37E', 
        'warning': '#FFAB00',
        'danger': '#DE350B',
        'info': '#00B8D9'
    }
    
    STATUS_COLORS = {
        'a fazer': '#DFE1E6',
        'em progresso': '#0052CC',
        'code review': '#FFAB00',
        'testing': '#00B8D9',
        'done': '#36B37E',
        'concluído': '#36B37E'
    }
    
    AGILE_COLORS = [
        '#0052CC', '#36B37E', '#FFAB00', '#DE350B', '#00B8D9',
        '#8777D9', '#FF5630', '#2684FF', '#00875A', '#FF8B00'
    ]
    
    @classmethod
    def get_default_layout(cls) -> Dict[str, Any]:
        """Retorna layout padrão para gráficos."""
        return {
            'font': {'family': 'Arial, sans-serif', 'size': 12},
            'paper_bgcolor': 'white',
            'plot_bgcolor': 'white',
            'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
        }
    
    @classmethod
    def apply_theme(cls, fig: go.Figure, theme: str = 'default') -> go.Figure:
        """
        Aplica tema ao gráfico.
        
        Args:
            fig: Figura plotly
            theme: Nome do tema
            
        Returns:
            Figura com tema aplicado
        """
        if theme == 'default':
            fig.update_layout(cls.get_default_layout())
        
        return fig