"""
Indicador de Distribuição de Conhecimento - Analisa riscos de dependência de pessoas.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from ..utils.log import info, warn, error


class KnowledgeDistributionIndicator:
    """
    Analisa a distribuição de conhecimento na equipe baseado em:
    - Concentração de trabalho por pessoa
    - Diversidade de tipos de tarefas por pessoa
    - Cobertura de componentes/áreas por pessoa
    - Risco de ponto único de falha (bus factor)
    """
    
    def __init__(self):
        """Inicializa o indicador de distribuição de conhecimento."""
        self.risk_thresholds = {
            'high': 0.7,      # >70% concentração = alto risco
            'medium': 0.5,    # 50-70% = médio risco  
            'low': 0.3        # <30% = baixo risco
        }
    
    def calculate_knowledge_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas de distribuição de conhecimento.
        
        Args:
            df: DataFrame com dados dos itens da sprint
            
        Returns:
            Dicionário com análise completa da distribuição
        """
        try:
            info("Calculando distribuição de conhecimento...")
            
            if df.empty or 'Responsável' not in df.columns:
                return self._get_default_result()
            
            # Limpar dados de responsáveis
            df_clean = self._clean_assignee_data(df)
            
            if df_clean.empty:
                return self._get_default_result()
            
            # 1. Análise de concentração de trabalho
            work_concentration = self._analyze_work_concentration(df_clean)
            
            # 2. Análise de diversidade de tarefas
            task_diversity = self._analyze_task_diversity(df_clean)
            
            # 3. Análise de cobertura de componentes
            component_coverage = self._analyze_component_coverage(df_clean)
            
            # 4. Cálculo do Bus Factor
            bus_factor = self._calculate_bus_factor(df_clean)
            
            # 5. Score geral de distribuição
            distribution_score = self._calculate_distribution_score(
                work_concentration, task_diversity, component_coverage, bus_factor
            )
            
            # 6. Identificar riscos
            risks = self._identify_risks(work_concentration, task_diversity, component_coverage)
            
            # 7. Gerar recomendações
            recommendations = self._generate_recommendations(risks, bus_factor)
            
            result = {
                'distribution_score': distribution_score,
                'bus_factor': bus_factor,
                'work_concentration': work_concentration,
                'task_diversity': task_diversity, 
                'component_coverage': component_coverage,
                'risks': risks,
                'recommendations': recommendations,
                'team_health': self._assess_team_health(distribution_score, bus_factor),
                'metrics': {
                    'total_people': len(work_concentration),
                    'items_per_person': {person: data['total_items'] 
                                       for person, data in work_concentration.items()},
                    'knowledge_areas': len(set(df_clean['Tipo'].dropna())),
                    'coverage_overlap': self._calculate_coverage_overlap(component_coverage)
                }
            }
            
            info(f"Distribuição calculada - Score: {distribution_score:.1f}, Bus Factor: {bus_factor}")
            return result
            
        except Exception as e:
            error(f"Erro ao calcular distribuição de conhecimento: {e}")
            return self._get_default_result()
    
    def _clean_assignee_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e padroniza dados de responsáveis."""
        df_clean = df.copy()
        
        # Remover itens sem responsável
        df_clean = df_clean[df_clean['Responsável'].notna()]
        df_clean = df_clean[df_clean['Responsável'].str.strip() != '']
        
        # Padronizar nomes (remover espaços extras, capitalizar)
        df_clean['Responsável'] = df_clean['Responsável'].str.strip().str.title()
        
        # Remover responsáveis genéricos
        generic_assignees = ['Unassigned', 'N/A', 'Não Atribuído', 'Admin', 'System']
        df_clean = df_clean[~df_clean['Responsável'].isin(generic_assignees)]
        
        return df_clean
    
    def _analyze_work_concentration(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Analisa concentração de trabalho por pessoa."""
        total_items = len(df)
        assignee_counts = df['Responsável'].value_counts()
        
        concentration_data = {}
        
        for assignee, count in assignee_counts.items():
            percentage = count / total_items
            concentration_level = self._get_concentration_level(percentage)
            
            concentration_data[assignee] = {
                'total_items': count,
                'percentage': round(percentage * 100, 1),
                'concentration_level': concentration_level,
                'risk_level': self._get_risk_level(percentage)
            }
        
        return concentration_data
    
    def _analyze_task_diversity(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Analisa diversidade de tipos de tarefas por pessoa."""
        diversity_data = {}
        
        if 'Tipo' not in df.columns:
            return diversity_data
        
        total_task_types = df['Tipo'].nunique()
        
        for assignee in df['Responsável'].unique():
            assignee_tasks = df[df['Responsável'] == assignee]
            task_types = assignee_tasks['Tipo'].nunique()
            
            diversity_ratio = task_types / total_task_types if total_task_types > 0 else 0
            
            diversity_data[assignee] = {
                'task_types_count': task_types,
                'total_task_types': total_task_types,
                'diversity_ratio': round(diversity_ratio, 2),
                'diversity_level': self._get_diversity_level(diversity_ratio),
                'task_types_list': list(assignee_tasks['Tipo'].unique())
            }
        
        return diversity_data
    
    def _analyze_component_coverage(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Analisa cobertura de componentes/áreas por pessoa."""
        coverage_data = {}
        
        # Tentar identificar componentes por diferentes campos
        component_field = None
        potential_fields = ['Componente', 'Component', 'Módulo', 'Sistema', 'Área']
        
        for field in potential_fields:
            if field in df.columns and df[field].notna().any():
                component_field = field
                break
        
        if not component_field:
            # Usar tipo de tarefa como proxy para componente
            component_field = 'Tipo'
        
        if component_field not in df.columns:
            return coverage_data
        
        total_components = df[component_field].nunique()
        
        for assignee in df['Responsável'].unique():
            assignee_work = df[df['Responsável'] == assignee]
            components = assignee_work[component_field].nunique()
            
            coverage_ratio = components / total_components if total_components > 0 else 0
            
            coverage_data[assignee] = {
                'components_count': components,
                'total_components': total_components,
                'coverage_ratio': round(coverage_ratio, 2),
                'coverage_level': self._get_coverage_level(coverage_ratio),
                'components_list': list(assignee_work[component_field].unique())
            }
        
        return coverage_data
    
    def _calculate_bus_factor(self, df: pd.DataFrame) -> int:
        """
        Calcula o Bus Factor - número mínimo de pessoas que precisam sair
        para que o projeto tenha problemas sérios.
        """
        if df.empty:
            return 0
        
        total_items = len(df)
        assignee_counts = df['Responsável'].value_counts().sort_values(ascending=False)
        
        cumulative_percentage = 0
        bus_factor = 0
        
        for assignee, count in assignee_counts.items():
            percentage = count / total_items
            cumulative_percentage += percentage
            bus_factor += 1
            
            # Se removendo essa pessoa + anteriores perdemos >50% do trabalho
            if cumulative_percentage >= 0.5:
                break
        
        return bus_factor
    
    def _calculate_distribution_score(self, work_concentration: Dict, task_diversity: Dict,
                                    component_coverage: Dict, bus_factor: int) -> float:
        """Calcula score geral de distribuição (0-100)."""
        if not work_concentration:
            return 50.0
        
        # 1. Score de concentração (melhor = mais distribuído)
        concentration_scores = []
        for data in work_concentration.values():
            if data['percentage'] <= 20:      # Ideal
                concentration_scores.append(100)
            elif data['percentage'] <= 30:    # Bom
                concentration_scores.append(80)
            elif data['percentage'] <= 50:    # Aceitável
                concentration_scores.append(60)
            elif data['percentage'] <= 70:    # Arriscado
                concentration_scores.append(30)
            else:                             # Crítico
                concentration_scores.append(10)
        
        concentration_score = np.mean(concentration_scores)
        
        # 2. Score de diversidade
        if task_diversity:
            diversity_scores = [data['diversity_ratio'] * 100 for data in task_diversity.values()]
            diversity_score = np.mean(diversity_scores)
        else:
            diversity_score = 50
        
        # 3. Score de cobertura
        if component_coverage:
            coverage_scores = [data['coverage_ratio'] * 100 for data in component_coverage.values()]
            coverage_score = np.mean(coverage_scores)
        else:
            coverage_score = 50
        
        # 4. Score de bus factor
        team_size = len(work_concentration)
        if team_size <= 2:
            bus_factor_score = 30  # Equipe muito pequena
        elif bus_factor >= team_size * 0.7:  # Bus factor alto
            bus_factor_score = 100
        elif bus_factor >= team_size * 0.5:  # Bus factor médio
            bus_factor_score = 70
        elif bus_factor >= team_size * 0.3:  # Bus factor baixo
            bus_factor_score = 40
        else:
            bus_factor_score = 20  # Bus factor crítico
        
        # Média ponderada
        final_score = (
            concentration_score * 0.4 +  # 40% - mais importante
            diversity_score * 0.25 +     # 25%
            coverage_score * 0.25 +      # 25%
            bus_factor_score * 0.1       # 10%
        )
        
        return round(final_score, 1)
    
    def _identify_risks(self, work_concentration: Dict, task_diversity: Dict,
                       component_coverage: Dict) -> List[Dict[str, Any]]:
        """Identifica riscos específicos na distribuição."""
        risks = []
        
        # Riscos de concentração
        for person, data in work_concentration.items():
            if data['percentage'] > 50:
                risks.append({
                    'type': 'high_concentration',
                    'severity': 'high',
                    'person': person,
                    'description': f"{person} está responsável por {data['percentage']:.1f}% das tarefas",
                    'impact': "Risco crítico se essa pessoa ficar indisponível"
                })
            elif data['percentage'] > 30:
                risks.append({
                    'type': 'medium_concentration', 
                    'severity': 'medium',
                    'person': person,
                    'description': f"{person} tem concentração alta de trabalho ({data['percentage']:.1f}%)",
                    'impact': "Possível gargalo na entrega"
                })
        
        # Riscos de baixa diversidade
        for person, data in task_diversity.items():
            if data['diversity_ratio'] < 0.3:
                risks.append({
                    'type': 'low_diversity',
                    'severity': 'medium',
                    'person': person,
                    'description': f"{person} trabalha em poucos tipos de tarefa ({data['task_types_count']} de {data['total_task_types']})",
                    'impact': "Conhecimento limitado pode restringir flexibilidade"
                })
        
        # Riscos de baixa cobertura
        for person, data in component_coverage.items():
            if data['coverage_ratio'] < 0.2:
                risks.append({
                    'type': 'low_coverage',
                    'severity': 'low',
                    'person': person,
                    'description': f"{person} tem baixa cobertura de componentes ({data['components_count']} de {data['total_components']})",
                    'impact': "Especialização excessiva pode ser limitante"
                })
        
        return risks
    
    def _generate_recommendations(self, risks: List[Dict], bus_factor: int) -> List[str]:
        """Gera recomendações baseadas nos riscos identificados."""
        recommendations = []
        
        # Recomendações por tipo de risco
        risk_types = [risk['type'] for risk in risks]
        
        if 'high_concentration' in risk_types:
            recommendations.extend([
                "🔴 CRÍTICO: Redistribuir tarefas imediatamente para reduzir dependência",
                "📚 Implementar pair programming para transferir conhecimento",
                "📋 Documentar processos críticos concentrados em uma pessoa"
            ])
        
        if 'medium_concentration' in risk_types:
            recommendations.extend([
                "🟡 Balancear carga de trabalho entre membros da equipe",
                "🤝 Criar rotação de responsabilidades"
            ])
        
        if 'low_diversity' in risk_types:
            recommendations.extend([
                "🔄 Implementar cross-training para ampliar conhecimento",
                "👥 Formar duplas mistas para compartilhar expertise"
            ])
        
        if bus_factor <= 2:
            recommendations.extend([
                "⚠️ Bus factor muito baixo - aumentar redundância de conhecimento",
                "📖 Criar documentação técnica detalhada"
            ])
        
        # Recomendações gerais
        if len(risks) > 3:
            recommendations.append("🏗️ Reestruturar organização da equipe para melhor distribuição")
        
        return recommendations[:6]  # Limitar a 6 recomendações
    
    def _assess_team_health(self, distribution_score: float, bus_factor: int) -> str:
        """Avalia saúde geral da distribuição de conhecimento."""
        if distribution_score >= 80 and bus_factor >= 3:
            return "Excelente"
        elif distribution_score >= 70 and bus_factor >= 2:
            return "Boa"
        elif distribution_score >= 60:
            return "Regular"
        elif distribution_score >= 40:
            return "Arriscada"
        else:
            return "Crítica"
    
    def _calculate_coverage_overlap(self, component_coverage: Dict) -> float:
        """Calcula sobreposição de cobertura entre pessoas."""
        if not component_coverage:
            return 0.0
        
        all_components = set()
        for data in component_coverage.values():
            all_components.update(data['components_list'])
        
        if not all_components:
            return 0.0
        
        overlap_count = 0
        for component in all_components:
            people_count = sum(
                1 for data in component_coverage.values()
                if component in data['components_list']
            )
            if people_count > 1:
                overlap_count += 1
        
        return round(overlap_count / len(all_components), 2)
    
    def _get_concentration_level(self, percentage: float) -> str:
        """Classifica nível de concentração."""
        if percentage > 0.5:
            return "Crítica"
        elif percentage > 0.3:
            return "Alta"
        elif percentage > 0.2:
            return "Média"
        else:
            return "Baixa"
    
    def _get_risk_level(self, percentage: float) -> str:
        """Classifica nível de risco."""
        if percentage > 0.7:
            return "Crítico"
        elif percentage > 0.5:
            return "Alto"
        elif percentage > 0.3:
            return "Médio"
        else:
            return "Baixo"
    
    def _get_diversity_level(self, ratio: float) -> str:
        """Classifica nível de diversidade."""
        if ratio >= 0.7:
            return "Alta"
        elif ratio >= 0.4:
            return "Média"
        else:
            return "Baixa"
    
    def _get_coverage_level(self, ratio: float) -> str:
        """Classifica nível de cobertura."""
        if ratio >= 0.6:
            return "Ampla"
        elif ratio >= 0.3:
            return "Média"
        else:
            return "Limitada"
    
    def _get_default_result(self) -> Dict[str, Any]:
        """Retorna resultado padrão quando não há dados suficientes."""
        return {
            'distribution_score': 50.0,
            'bus_factor': 1,
            'work_concentration': {},
            'task_diversity': {},
            'component_coverage': {},
            'risks': [],
            'recommendations': ["Dados insuficientes para análise de distribuição"],
            'team_health': "Indeterminada",
            'metrics': {
                'total_people': 0,
                'items_per_person': {},
                'knowledge_areas': 0,
                'coverage_overlap': 0.0
            }
        }
    
    def create_concentration_chart(self, knowledge_data: Dict[str, Any]) -> go.Figure:
        """Cria gráfico de concentração de trabalho."""
        try:
            work_concentration = knowledge_data['work_concentration']
            
            if not work_concentration:
                return go.Figure()
            
            people = list(work_concentration.keys())
            percentages = [data['percentage'] for data in work_concentration.values()]
            items = [data['total_items'] for data in work_concentration.values()]
            
            # Cores baseadas no risco
            colors = []
            for data in work_concentration.values():
                risk = data['risk_level']
                if risk == 'Crítico':
                    colors.append('#dc3545')
                elif risk == 'Alto':
                    colors.append('#fd7e14')
                elif risk == 'Médio':
                    colors.append('#ffc107')
                else:
                    colors.append('#28a745')
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=people,
                y=percentages,
                text=[f'{p:.1f}%<br>({i} itens)' for p, i in zip(percentages, items)],
                textposition='outside',
                marker_color=colors,
                hovertemplate='<b>%{x}</b><br>Concentração: %{y:.1f}%<br>Itens: %{customdata}<extra></extra>',
                customdata=items
            ))
            
            # Linha de alerta (30%)
            fig.add_hline(y=30, line_dash="dash", line_color="orange", 
                         annotation_text="Limite Recomendado (30%)")
            
            # Linha crítica (50%)
            fig.add_hline(y=50, line_dash="dash", line_color="red",
                         annotation_text="Nível Crítico (50%)")
            
            fig.update_layout(
                title="Concentração de Trabalho por Pessoa",
                xaxis_title="Pessoas",
                yaxis_title="% do Trabalho Total",
                yaxis=dict(range=[0, max(percentages) * 1.2]),
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            error(f"Erro ao criar gráfico de concentração: {e}")
            return go.Figure()
    
    def create_diversity_chart(self, knowledge_data: Dict[str, Any]) -> go.Figure:
        """Cria gráfico de diversidade de tarefas."""
        try:
            task_diversity = knowledge_data['task_diversity']
            
            if not task_diversity:
                return go.Figure()
            
            people = list(task_diversity.keys())
            diversity_ratios = [data['diversity_ratio'] for data in task_diversity.values()]
            task_counts = [data['task_types_count'] for data in task_diversity.values()]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=people,
                y=diversity_ratios,
                text=[f'{r:.2f}<br>({c} tipos)' for r, c in zip(diversity_ratios, task_counts)],
                textposition='outside',
                marker_color='rgba(54, 162, 235, 0.7)',
                hovertemplate='<b>%{x}</b><br>Diversidade: %{y:.2f}<br>Tipos de tarefa: %{customdata}<extra></extra>',
                customdata=task_counts
            ))
            
            fig.update_layout(
                title="Diversidade de Tipos de Tarefa por Pessoa",
                xaxis_title="Pessoas",
                yaxis_title="Ratio de Diversidade (0-1)",
                yaxis=dict(range=[0, 1]),
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            error(f"Erro ao criar gráfico de diversidade: {e}")
            return go.Figure()
    
    def create_bus_factor_chart(self, knowledge_data: Dict[str, Any]) -> go.Figure:
        """Cria visualização do Bus Factor."""
        try:
            work_concentration = knowledge_data['work_concentration']
            bus_factor = knowledge_data['bus_factor']
            
            if not work_concentration:
                return go.Figure()
            
            # Ordenar por concentração (maior primeiro)
            sorted_people = sorted(
                work_concentration.items(),
                key=lambda x: x[1]['percentage'],
                reverse=True
            )
            
            people = [item[0] for item in sorted_people]
            percentages = [item[1]['percentage'] for item in sorted_people]
            
            # Calcular percentagem cumulativa
            cumulative = np.cumsum(percentages)
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Barras individuais
            fig.add_trace(
                go.Bar(
                    x=people,
                    y=percentages,
                    name="Concentração Individual",
                    marker_color='rgba(54, 162, 235, 0.7)'
                ),
                secondary_y=False,
            )
            
            # Linha cumulativa
            fig.add_trace(
                go.Scatter(
                    x=people,
                    y=cumulative,
                    mode='lines+markers',
                    name="Concentração Cumulativa",
                    line=dict(color='red', width=3),
                    marker=dict(size=8)
                ),
                secondary_y=True,
            )
            
            # Marcar bus factor
            if bus_factor <= len(people):
                fig.add_vline(
                    x=bus_factor - 0.5,
                    line_dash="dash",
                    line_color="orange",
                    annotation_text=f"Bus Factor: {bus_factor}"
                )
            
            # Linha de 50%
            fig.add_hline(
                y=50,
                line_dash="dash", 
                line_color="red",
                annotation_text="50% do Trabalho",
                secondary_y=True
            )
            
            fig.update_xaxes(title_text="Pessoas (ordenadas por concentração)")
            fig.update_yaxes(title_text="% Individual", secondary_y=False)
            fig.update_yaxes(title_text="% Cumulativa", secondary_y=True)
            
            fig.update_layout(
                title=f"Análise do Bus Factor (Bus Factor = {bus_factor})",
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            error(f"Erro ao criar gráfico de bus factor: {e}")
            return go.Figure()