"""
Módulo central para cálculo de métricas do dashboard.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from ..utils_normalize import normalize, canonical_type
from ..config import config


class MetricsCalculator:
    """Calculadora centralizada de métricas."""
    
    @staticmethod
    def calculate_executive_summary(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula resumo executivo da sprint.
        
        Args:
            df: DataFrame com dados da sprint
            
        Returns:
            Dicionário com métricas executivas
        """
        # Filtrar apenas itens de interesse usando tipo canônico
        tipos_interesse = {'História', 'Débito Técnico', 'Spike', 'Bug', 'Impedimento'}
        df_tmp_tipos = df.copy()
        df_tmp_tipos['TipoCanon'] = df_tmp_tipos['Tipo de Item'].apply(
            lambda x: canonical_type(normalize(x))
        )
        df_exec = df_tmp_tipos[df_tmp_tipos['TipoCanon'].isin(tipos_interesse)]

        # Contadores por tipo (canônico)
        contador_tipos = df_exec['TipoCanon'].value_counts()
        total_itens_exec = len(df_exec)

        return {
            'total_itens': total_itens_exec,
            'historias': contador_tipos.get('História', 0),
            'debitos': contador_tipos.get('Débito Técnico', 0),
            'spikes': contador_tipos.get('Spike', 0),
            'bugs': contador_tipos.get('Bug', 0),
            'impedimentos': contador_tipos.get('Impedimento', 0),
            'contador_tipos': contador_tipos.to_dict(),
            'df_executivo': df_exec
        }
    
    @staticmethod
    def calculate_velocity_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas de velocidade.
        
        Args:
            df: DataFrame com dados
            
        Returns:
            Dicionário com métricas de velocidade
        """
        # Filtrar apenas itens com story points
        tipos_validos_norm = {
            normalize('História'), 
            normalize('Débito Técnico'), 
            normalize('Spike')
        }
        mask_tipos = df['Tipo de Item'].apply(
            lambda x: normalize(x) in tipos_validos_norm
        )
        df_sp = df[mask_tipos & (df['Story Points'] > 0)].copy()
        
        if df_sp.empty:
            return {
                'total_story_points': 0,
                'committed_story_points': 0,
                'completed_story_points': 0,
                'completion_rate': 0.0,
                'average_story_points': 0.0
            }
        
        total_sp = df_sp['Story Points'].sum()
        
        # Assumir que itens "Done"/"Concluído" estão completos
        status_concluido = df_sp['Status'].str.contains(
            'Done|Concluído|Resolvido|Fechado', 
            case=False, 
            na=False
        )
        completed_sp = df_sp[status_concluido]['Story Points'].sum()
        
        completion_rate = (completed_sp / total_sp * 100) if total_sp > 0 else 0.0
        avg_sp = df_sp['Story Points'].mean()
        
        return {
            'total_story_points': int(total_sp),
            'committed_story_points': int(total_sp),  # Assumir todos foram commitados
            'completed_story_points': int(completed_sp),
            'completion_rate': round(completion_rate, 1),
            'average_story_points': round(avg_sp, 1)
        }
    
    @staticmethod
    def calculate_quality_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas de qualidade.
        
        Args:
            df: DataFrame com dados
            
        Returns:
            Dicionário com métricas de qualidade
        """
        # Bugs e impedimentos
        df_bugs = df[df['Tipo de Item'].str.fullmatch(r"(?i)bug", na=False)]
        df_impedimentos = df[df['Tipo de Item'].str.contains(
            'Impedimento', case=False, na=False
        )]
        
        total_itens = len(df)
        total_bugs = len(df_bugs)
        total_impedimentos = len(df_impedimentos)
        
        # Taxa de defeitos
        bug_rate = (total_bugs / total_itens * 100) if total_itens > 0 else 0.0
        
        # Taxa de impedimentos
        impediment_rate = (total_impedimentos / total_itens * 100) if total_itens > 0 else 0.0
        
        return {
            'total_bugs': total_bugs,
            'total_impediments': total_impedimentos,
            'bug_rate': round(bug_rate, 1),
            'impediment_rate': round(impediment_rate, 1),
            'quality_score': max(0, 100 - bug_rate - impediment_rate)  # Score simples
        }
    
    @staticmethod
    def calculate_team_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas de time.
        
        Args:
            df: DataFrame com dados
            
        Returns:
            Dicionário com métricas de time
        """
        if 'Responsável' not in df.columns:
            return {
                'total_members': 0,
                'items_per_member': {},
                'workload_distribution': {}
            }
        
        # Distribuição de trabalho por membro
        member_workload = df['Responsável'].value_counts()
        total_members = len(member_workload)
        
        # Calcular distribuição percentual
        workload_pct = (member_workload / len(df) * 100).round(1)
        
        return {
            'total_members': total_members,
            'items_per_member': member_workload.to_dict(),
            'workload_distribution': workload_pct.to_dict(),
            'most_loaded_member': member_workload.index[0] if not member_workload.empty else None,
            'max_items': member_workload.iloc[0] if not member_workload.empty else 0
        }
    
    @staticmethod
    def calculate_flow_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas de fluxo (Kanban).
        
        Args:
            df: DataFrame com dados
            
        Returns:
            Dicionário com métricas de fluxo
        """
        # WIP atual
        status_prog = {s.lower() for s in config.STATUS_EM_PROGRESSO}
        wip_items = df[
            df['Status'].apply(lambda s: isinstance(s, str) and s.lower() in status_prog) & 
            df['Data Resolução'].isna()
        ]
        
        # Throughput (itens concluídos)
        throughput_items = df[df['Data Resolução'].notna()]
        
        # Cycle time médio (para itens resolvidos)
        cycle_times = []
        if not throughput_items.empty:
            for _, item in throughput_items.iterrows():
                if pd.notna(item['Data Criação']) and pd.notna(item['Data Resolução']):
                    created = pd.to_datetime(item['Data Criação'])
                    resolved = pd.to_datetime(item['Data Resolução'])
                    cycle_time = (resolved - created).days
                    cycle_times.append(cycle_time)
        
        avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0
        
        return {
            'wip_count': len(wip_items),
            'throughput_count': len(throughput_items),
            'average_cycle_time': round(avg_cycle_time, 1),
            'cycle_time_distribution': cycle_times,
            'flow_efficiency': 0.0  # Placeholder - needs more data to calculate
        }


class DashboardMetrics:
    """Fachada para todas as métricas do dashboard."""
    
    def __init__(self, df: pd.DataFrame):
        """
        Inicializa com DataFrame principal.
        
        Args:
            df: DataFrame com dados da sprint
        """
        self.df = df
        self.calculator = MetricsCalculator()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Calcula todas as métricas disponíveis.
        
        Returns:
            Dicionário com todas as métricas organizadas por categoria
        """
        return {
            'executive': self.calculator.calculate_executive_summary(self.df),
            'velocity': self.calculator.calculate_velocity_metrics(self.df),
            'quality': self.calculator.calculate_quality_metrics(self.df),
            'team': self.calculator.calculate_team_metrics(self.df),
            'flow': self.calculator.calculate_flow_metrics(self.df)
        }
    
    def get_executive_metrics(self) -> Dict[str, Any]:
        """Retorna apenas métricas executivas."""
        return self.calculator.calculate_executive_summary(self.df)
    
    def get_velocity_metrics(self) -> Dict[str, Any]:
        """Retorna apenas métricas de velocidade."""
        return self.calculator.calculate_velocity_metrics(self.df)
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Retorna apenas métricas de qualidade."""
        return self.calculator.calculate_quality_metrics(self.df)
    
    def get_team_metrics(self) -> Dict[str, Any]:
        """Retorna apenas métricas de time."""
        return self.calculator.calculate_team_metrics(self.df)
    
    def get_flow_metrics(self) -> Dict[str, Any]:
        """Retorna apenas métricas de fluxo."""
        return self.calculator.calculate_flow_metrics(self.df)