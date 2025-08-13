"""
Indicador de Eficiência de Sprint - Combina velocidade, qualidade e previsibilidade.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..utils.log import info, warn, error


class SprintEfficiencyIndicator:
    """
    Calcula um índice de eficiência que combina:
    - Velocidade: Stories entregues vs planejadas
    - Qualidade: Taxa de bugs vs features 
    - Previsibilidade: Acurácia das estimativas
    - Estabilidade: Mudanças de escopo durante sprint
    """
    
    def __init__(self):
        """Inicializa o indicador de eficiência."""
        self.weights = {
            'velocity': 0.3,      # 30% - Entrega conforme planejado
            'quality': 0.25,      # 25% - Baixa taxa de bugs
            'predictability': 0.25, # 25% - Estimativas precisas
            'stability': 0.2      # 20% - Escopo estável
        }
    
    def calculate_efficiency_score(self, df: pd.DataFrame, sprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula o score de eficiência da sprint.
        
        Args:
            df: DataFrame com dados dos itens da sprint
            sprint_data: Dados adicionais da sprint (datas, metas, etc.)
            
        Returns:
            Dicionário com scores detalhados e índice final
        """
        try:
            info("Calculando eficiência de sprint...")
            
            # 1. Score de Velocidade
            velocity_score = self._calculate_velocity_score(df, sprint_data)
            
            # 2. Score de Qualidade  
            quality_score = self._calculate_quality_score(df)
            
            # 3. Score de Previsibilidade
            predictability_score = self._calculate_predictability_score(df)
            
            # 4. Score de Estabilidade
            stability_score = self._calculate_stability_score(df, sprint_data)
            
            # Calcular índice final
            final_score = (
                velocity_score * self.weights['velocity'] +
                quality_score * self.weights['quality'] + 
                predictability_score * self.weights['predictability'] +
                stability_score * self.weights['stability']
            )
            
            # Classificação do score
            classification = self._classify_efficiency(final_score)
            
            result = {
                'final_score': round(final_score, 2),
                'classification': classification,
                'components': {
                    'velocity': {
                        'score': round(velocity_score, 2),
                        'weight': self.weights['velocity'],
                        'contribution': round(velocity_score * self.weights['velocity'], 2)
                    },
                    'quality': {
                        'score': round(quality_score, 2),
                        'weight': self.weights['quality'],
                        'contribution': round(quality_score * self.weights['quality'], 2)
                    },
                    'predictability': {
                        'score': round(predictability_score, 2),
                        'weight': self.weights['predictability'],
                        'contribution': round(predictability_score * self.weights['predictability'], 2)
                    },
                    'stability': {
                        'score': round(stability_score, 2),
                        'weight': self.weights['stability'],
                        'contribution': round(stability_score * self.weights['stability'], 2)
                    }
                },
                'insights': self._generate_insights(velocity_score, quality_score, 
                                                  predictability_score, stability_score),
                'recommendations': self._generate_recommendations(velocity_score, quality_score,
                                                                predictability_score, stability_score)
            }
            
            info(f"Eficiência calculada: {final_score:.2f} ({classification})")
            return result
            
        except Exception as e:
            error(f"Erro ao calcular eficiência: {e}")
            return self._get_default_result()
    
    def _calculate_velocity_score(self, df: pd.DataFrame, sprint_data: Dict[str, Any]) -> float:
        """Calcula score baseado na velocidade de entrega."""
        try:
            # Itens planejados vs entregues
            total_items = len(df)
            completed_items = len(df[df['Status Categoria'] == 'Done'])
            
            if total_items == 0:
                return 0.0
            
            delivery_rate = completed_items / total_items
            
            # Penalizar entregas muito baixas, premiar entregas consistentes
            if delivery_rate >= 0.9:
                score = 100
            elif delivery_rate >= 0.8:
                score = 90
            elif delivery_rate >= 0.7:
                score = 75
            elif delivery_rate >= 0.6:
                score = 60
            elif delivery_rate >= 0.5:
                score = 40
            else:
                score = delivery_rate * 50  # Penalização severa
            
            # Bonus para sprints que entregaram acima do planejado
            if delivery_rate > 1.0:
                score = min(100, score + ((delivery_rate - 1.0) * 20))
            
            return score
            
        except Exception:
            return 50.0  # Score neutro em caso de erro
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """Calcula score baseado na qualidade (bugs vs features)."""
        try:
            # Identificar bugs vs features/stories
            bug_keywords = ['bug', 'defeito', 'erro', 'falha', 'problema']
            
            df_lower = df['Tipo'].str.lower() if 'Tipo' in df.columns else pd.Series()
            
            bugs = df_lower.str.contains('|'.join(bug_keywords), na=False).sum()
            total_items = len(df)
            
            if total_items == 0:
                return 100.0
            
            bug_rate = bugs / total_items
            
            # Score inversamente proporcional à taxa de bugs
            if bug_rate <= 0.05:  # <= 5% bugs
                score = 100
            elif bug_rate <= 0.1:  # <= 10% bugs
                score = 85
            elif bug_rate <= 0.15:  # <= 15% bugs
                score = 70
            elif bug_rate <= 0.2:   # <= 20% bugs
                score = 55
            elif bug_rate <= 0.3:   # <= 30% bugs
                score = 35
            else:
                score = max(10, 100 - (bug_rate * 200))  # Penalização severa
            
            return score
            
        except Exception:
            return 75.0  # Score padrão razoável
    
    def _calculate_predictability_score(self, df: pd.DataFrame) -> float:
        """Calcula score baseado na acurácia das estimativas."""
        try:
            # Verificar se existem dados de estimativa vs tempo real
            if 'Story Points' not in df.columns or 'Dias para Resolução' not in df.columns:
                return 70.0  # Score padrão quando não há dados suficientes
            
            # Filtrar itens completos com estimativas
            completed_df = df[
                (df['Status Categoria'] == 'Done') & 
                (df['Story Points'].notna()) &
                (df['Dias para Resolução'].notna()) &
                (df['Story Points'] > 0)
            ].copy()
            
            if len(completed_df) < 3:  # Poucos dados para análise
                return 70.0
            
            # Calcular desvio entre estimado e real
            # Assumir que 1 story point = 1 dia (ajustável)
            estimated_days = completed_df['Story Points']
            actual_days = completed_df['Dias para Resolução']
            
            # Calcular erro percentual absoluto médio
            percentage_errors = abs((actual_days - estimated_days) / estimated_days) * 100
            mean_error = percentage_errors.mean()
            
            # Score baseado na precisão
            if mean_error <= 20:      # <= 20% erro
                score = 100
            elif mean_error <= 30:    # <= 30% erro
                score = 85
            elif mean_error <= 50:    # <= 50% erro
                score = 70
            elif mean_error <= 75:    # <= 75% erro
                score = 50
            elif mean_error <= 100:   # <= 100% erro
                score = 30
            else:
                score = max(10, 100 - mean_error)
            
            return score
            
        except Exception:
            return 70.0
    
    def _calculate_stability_score(self, df: pd.DataFrame, sprint_data: Dict[str, Any]) -> float:
        """Calcula score baseado na estabilidade do escopo."""
        try:
            # Analisar mudanças durante a sprint
            # Itens adicionados durante sprint (Data Criação > Início Sprint)
            # Itens removidos (Status = Removido ou similar)
            
            sprint_start = sprint_data.get('start_date')
            if not sprint_start:
                return 80.0  # Score padrão sem data de início
            
            if isinstance(sprint_start, str):
                sprint_start = datetime.fromisoformat(sprint_start)
            
            # Itens criados após início da sprint
            if 'Data Criação' in df.columns:
                df_temp = df.copy()
                df_temp['Data Criação'] = pd.to_datetime(df_temp['Data Criação'], errors='coerce')
                
                items_added_during = len(df_temp[df_temp['Data Criação'] > sprint_start])
                total_items = len(df)
                
                if total_items == 0:
                    return 80.0
                
                change_rate = items_added_during / total_items
                
                # Score baseado na estabilidade
                if change_rate <= 0.1:     # <= 10% mudança
                    score = 100
                elif change_rate <= 0.2:   # <= 20% mudança  
                    score = 80
                elif change_rate <= 0.3:   # <= 30% mudança
                    score = 60
                elif change_rate <= 0.5:   # <= 50% mudança
                    score = 40
                else:
                    score = max(10, 100 - (change_rate * 100))
                
                return score
            
            return 80.0  # Score padrão sem dados de criação
            
        except Exception:
            return 80.0
    
    def _classify_efficiency(self, score: float) -> str:
        """Classifica o score de eficiência."""
        if score >= 90:
            return "Excelente"
        elif score >= 80:
            return "Muito Boa" 
        elif score >= 70:
            return "Boa"
        elif score >= 60:
            return "Regular"
        elif score >= 50:
            return "Baixa"
        else:
            return "Crítica"
    
    def _generate_insights(self, velocity: float, quality: float, 
                          predictability: float, stability: float) -> List[str]:
        """Gera insights baseados nos scores."""
        insights = []
        
        # Análise de velocidade
        if velocity >= 85:
            insights.append("🚀 Excelente taxa de entrega - equipe está produtiva")
        elif velocity < 60:
            insights.append("⚠️ Taxa de entrega baixa - revisar planejamento ou capacidade")
        
        # Análise de qualidade
        if quality >= 85:
            insights.append("✅ Baixa taxa de bugs - qualidade alta")
        elif quality < 60:
            insights.append("🐛 Alta taxa de bugs - investir em testes e revisões")
        
        # Análise de previsibilidade
        if predictability >= 80:
            insights.append("🎯 Estimativas precisas - boa maturidade da equipe")
        elif predictability < 60:
            insights.append("📊 Estimativas imprecisas - refinar processo de planning")
        
        # Análise de estabilidade
        if stability >= 85:
            insights.append("🛡️ Escopo estável - bom planejamento inicial")
        elif stability < 60:
            insights.append("🌪️ Muito mudanças de escopo - melhorar refinamento")
        
        return insights
    
    def _generate_recommendations(self, velocity: float, quality: float,
                                predictability: float, stability: float) -> List[str]:
        """Gera recomendações de melhoria."""
        recommendations = []
        
        # Maior problema primeiro
        scores = {
            'velocity': velocity,
            'quality': quality, 
            'predictability': predictability,
            'stability': stability
        }
        
        lowest_score = min(scores.items(), key=lambda x: x[1])
        
        if lowest_score[0] == 'velocity' and lowest_score[1] < 70:
            recommendations.append("1. Reduzir escopo do sprint ou aumentar capacidade da equipe")
            recommendations.append("2. Identificar impedimentos que afetam a entrega")
        
        if lowest_score[0] == 'quality' and lowest_score[1] < 70:
            recommendations.append("1. Implementar mais testes automatizados")
            recommendations.append("2. Fazer code review obrigatório")
            recommendations.append("3. Incluir critérios de qualidade na Definition of Done")
        
        if lowest_score[0] == 'predictability' and lowest_score[1] < 70:
            recommendations.append("1. Treinar equipe em técnicas de estimativa (Planning Poker)")
            recommendations.append("2. Quebrar histórias grandes em menores")
            recommendations.append("3. Usar dados históricos para calibrar estimativas")
        
        if lowest_score[0] == 'stability' and lowest_score[1] < 70:
            recommendations.append("1. Melhorar refinamento antes do planning")
            recommendations.append("2. Definir critérios claros para mudanças de escopo")
            recommendations.append("3. Educar stakeholders sobre impacto das mudanças")
        
        return recommendations
    
    def _get_default_result(self) -> Dict[str, Any]:
        """Retorna resultado padrão em caso de erro."""
        return {
            'final_score': 50.0,
            'classification': 'Regular',
            'components': {
                'velocity': {'score': 50, 'weight': 0.3, 'contribution': 15},
                'quality': {'score': 50, 'weight': 0.25, 'contribution': 12.5},
                'predictability': {'score': 50, 'weight': 0.25, 'contribution': 12.5},
                'stability': {'score': 50, 'weight': 0.2, 'contribution': 10}
            },
            'insights': ["Dados insuficientes para análise detalhada"],
            'recommendations': ["Coletar mais dados para análise precisa"]
        }
    
    def create_efficiency_chart(self, efficiency_data: Dict[str, Any]) -> go.Figure:
        """
        Cria gráfico de radar mostrando os componentes da eficiência.
        
        Args:
            efficiency_data: Dados de eficiência calculados
            
        Returns:
            Figura do Plotly
        """
        try:
            components = efficiency_data['components']
            
            categories = ['Velocidade', 'Qualidade', 'Previsibilidade', 'Estabilidade']
            values = [
                components['velocity']['score'],
                components['quality']['score'], 
                components['predictability']['score'],
                components['stability']['score']
            ]
            
            # Fechar o radar
            values.append(values[0])
            categories.append(categories[0])
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='Eficiência',
                fillcolor='rgba(0, 123, 255, 0.3)',
                line_color='rgba(0, 123, 255, 1)',
                line_width=3
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )
                ),
                title=f"Radar de Eficiência - Score: {efficiency_data['final_score']} ({efficiency_data['classification']})",
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            error(f"Erro ao criar gráfico de eficiência: {e}")
            # Retornar gráfico vazio
            return go.Figure()
    
    def create_components_chart(self, efficiency_data: Dict[str, Any]) -> go.Figure:
        """
        Cria gráfico de barras com os componentes da eficiência.
        
        Args:
            efficiency_data: Dados de eficiência calculados
            
        Returns:
            Figura do Plotly
        """
        try:
            components = efficiency_data['components']
            
            categories = ['Velocidade', 'Qualidade', 'Previsibilidade', 'Estabilidade']
            scores = [
                components['velocity']['score'],
                components['quality']['score'],
                components['predictability']['score'], 
                components['stability']['score']
            ]
            contributions = [
                components['velocity']['contribution'],
                components['quality']['contribution'],
                components['predictability']['contribution'],
                components['stability']['contribution']
            ]
            
            # Cores baseadas no score
            colors = []
            for score in scores:
                if score >= 80:
                    colors.append('#28a745')  # Verde
                elif score >= 60:
                    colors.append('#ffc107')  # Amarelo
                else:
                    colors.append('#dc3545')  # Vermelho
            
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Scores dos Componentes', 'Contribuição para Score Final'),
                specs=[[{"type": "bar"}, {"type": "bar"}]]
            )
            
            # Gráfico de scores
            fig.add_trace(
                go.Bar(
                    x=categories,
                    y=scores,
                    marker_color=colors,
                    text=[f'{s:.1f}' for s in scores],
                    textposition='outside'
                ),
                row=1, col=1
            )
            
            # Gráfico de contribuições
            fig.add_trace(
                go.Bar(
                    x=categories,
                    y=contributions,
                    marker_color='rgba(0, 123, 255, 0.7)',
                    text=[f'{c:.1f}' for c in contributions],
                    textposition='outside'
                ),
                row=1, col=2
            )
            
            fig.update_layout(
                title_text=f"Análise Detalhada da Eficiência - Score Final: {efficiency_data['final_score']}",
                showlegend=False
            )
            
            fig.update_yaxes(title_text="Score", row=1, col=1, range=[0, 100])
            fig.update_yaxes(title_text="Contribuição", row=1, col=2)
            
            return fig
            
        except Exception as e:
            error(f"Erro ao criar gráfico de componentes: {e}")
            return go.Figure()