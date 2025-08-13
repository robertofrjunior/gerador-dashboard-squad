#!/usr/bin/env python3
"""
Interface Web para Dashboard de Análise de Sprint Jira
Desenvolvido com Streamlit para facilitar a visualização das métricas.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Importar módulos do projeto
from jiraproject.sprint_service import analisar_sprint
from jiraproject.utils_constants import TIPOS_AGEIS_CANON
from jiraproject.utils_normalize import normalize, canonical_type
from jiraproject.config import config
from jiraproject.utils_arrow import make_display_copy
from jiraproject.utils_calculations import calc_resolution_days, get_resolved_items, calculate_time_statistics, group_by_time_stats
from jiraproject.services import jira as jira_service
from jiraproject.utils.log import info, ok, warn, error
from jiraproject.utils.ui import status_color, build_column_config, metric, pct_delta, pie, bar, tempo_stats_metrics, scatter
from jiraproject.components import FilterComponents, apply_filters, show_filter_summary
from jiraproject.charts import ChartFactory
from jiraproject.metrics import DashboardMetrics


# Helpers internos para reduzir duplicação (deprecated - usar utils_calculations)
def calc_dias(df: pd.DataFrame, created_col: str = 'Data Criação', resolved_col: str = 'Data Resolução', out_col: str = 'Dias para Resolução') -> pd.DataFrame:
    return calc_resolution_days(df, created_col, resolved_col, out_col)


def show_df(df: pd.DataFrame, **kwargs) -> None:
    """Exibe DataFrame usando make_display_copy para compatibilidade."""
    st.dataframe(make_display_copy(df), **kwargs)
@st.cache_data(show_spinner="Buscando sprints do projeto...", ttl=config.CACHE_TTL_SPRINTS)
def buscar_sprints_do_projeto_cache(_projeto_validado: str) -> Optional[Dict[str, Any]]:
    """Busca sprints do board com cache para evitar múltiplas chamadas."""
    from jiraproject.services.jira import buscar_board_do_projeto, buscar_sprints_do_board
    
    try:
        board_id = buscar_board_do_projeto(_projeto_validado)
        if board_id:
            return buscar_sprints_do_board(board_id)
    except Exception as e:
        warn(f"Erro ao buscar sprints: {e}")
    return None

@st.cache_data(show_spinner="Validando projeto...")
def resolver_nome_projeto(_projeto_input: str) -> Tuple[str, bool, str]:
    """
    Resolve o nome correto do projeto testando variações comuns.
    
    Returns:
        tuple: (projeto_correto, sucesso, mensagem)
    """
    from jiraproject.services.jira import validar_projeto
    
    # Lista de variações para testar baseadas no input
    variações = [_projeto_input.strip()]
    
    input_lower = _projeto_input.lower().strip()
    
    # Adicionar variações baseadas em padrões conhecidos
    if input_lower in ['smd', 'squad marketing digital']:
        variações.extend(['SMD', '[DIGITAL] Sites / Marketing', 'smd'])
    elif input_lower in ['vac', 'vacinas']:
        variações.extend(['VAC', '[DIGITAL] Vacinas', 'vac']) 
    elif 'jiraproject' in input_lower:
        variações.extend(['[DIGITAL] CredCesta CORE', 'CredCesta', 'CREDCESTA'])
    elif input_lower in ['pv', 'portal vendedor']:
        variações.extend(['PV', '[DIGITAL] Portal do Vendedor', 'pv'])
    
    # Adicionar variações de case
    variações.extend([
        _projeto_input.upper(),
        _projeto_input.lower(),
        _projeto_input.title()
    ])
    
    # Remover duplicatas mantendo ordem
    variações_unicas = []
    for v in variações:
        if v and v not in variações_unicas:
            variações_unicas.append(v)
    
    info(f"Testando variações para '{_projeto_input}': {variações_unicas}")
    
    # Testar cada variação
    for variação in variações_unicas:
        try:
            é_válido, mensagem = validar_projeto(variação)
            if é_válido:
                ok(f"Projeto encontrado: '{variação}' - {mensagem}")
                return variação, True, mensagem
            else:
                warn(f"'{variação}': {mensagem}")
        except Exception as e:
            warn(f"Erro ao testar '{variação}': {e}")
            continue
    
    return _projeto_input, False, f"Nenhuma variação válida encontrada para '{_projeto_input}'"

@st.cache_data(show_spinner="Validando sprints...")
def validar_sprints_especificas(_projeto: str, _sprint_ids: List[int]) -> Tuple[List[int], List[int]]:
    """
    Valida apenas os IDs de sprint especificados pelo usuário.
    NÃO faz busca exaustiva.
    
    Args:
        _projeto: Nome do projeto
        _sprint_ids: Lista de IDs de sprint para validar
        
    Returns:
        tuple: (sprints_validas, sprints_invalidas)
    """
    sprints_validas = []
    sprints_invalidas = []
    
    info(f"Validando {len(_sprint_ids)} sprints para projeto '{_projeto}'")
    
    for sprint_id in _sprint_ids:
        try:
            # Tenta buscar apenas 1 issue para validar se a sprint existe
            from jiraproject.services.jira import buscar_sprint_jira
            resultado = buscar_sprint_jira(_projeto, sprint_id)
            
            if resultado and resultado.get('total', 0) > 0:
                sprints_validas.append(sprint_id)
                ok(f"Sprint {sprint_id}: válida ({resultado.get('total')} issues)")
            else:
                sprints_invalidas.append(sprint_id)
                warn(f"Sprint {sprint_id}: sem issues")
                
        except Exception as e:
            sprints_invalidas.append(sprint_id)
            error(f"Sprint {sprint_id}: erro - {str(e)[:50]}")
    
    return sprints_validas, sprints_invalidas

@st.cache_data(show_spinner="Carregando projetos do Jira...", ttl=config.CACHE_TTL_PROJETOS)
def listar_projetos_cache() -> List[Dict[str, str]]:
    """Retorna a lista de projetos do Jira (key e name)."""
    try:
        return jira_service.listar_projetos()
    except Exception as e:
        error(f"Erro ao carregar projetos: {e}")
        return []

# Configuração da página
st.set_page_config(
    page_title="Dashboard Sprint Jira",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações da Análise")
    # Modelo de trabalho
    modelo_trabalho = st.selectbox(
        "Modelo de Trabalho",
        options=["Scrum", "Kanban"],
        index=0,
        key="modelo_trabalho",
        help="Selecione o modelo de trabalho. Scrum mantém as abas atuais; Kanban adiciona uma aba com métricas de fluxo."
    )
    
    # Seção de entrada de dados
    st.subheader("Dados da Sprint")
    
    # Lista de projetos comuns para ajudar o usuário
    projetos_sugeridos = config.PROJETOS_SUGERIDOS
    
    # Seletor único de Squad/Board
    squads = jira_service.listar_squads()
    squad_selecionada = st.selectbox(
        "Selecione a Squad/Board",
        options=squads if squads else [],
        format_func=lambda s: f"{s['key']} — {s['board_name']} ({s['name']})" if isinstance(s, dict) else str(s),
        key="squad_select",
    )
    if squad_selecionada:
        st.session_state['projeto_key'] = squad_selecionada['key']  # ex.: VAC
        st.session_state['projeto_name'] = squad_selecionada['name']
        st.session_state['board_id'] = squad_selecionada['board_id']
        st.session_state['projeto'] = squad_selecionada['key']
        # Limpa dados anteriores ao trocar de squad
        keys_to_clear = ['sprints_selecionadas', 'sprints_validadas', 'df', 'sprint_info', 'selectbox_sprint', 'sprint_ids_input', 'last_loaded_signature']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.cache_data.clear()

    projeto_validado = st.session_state.get('projeto_key')
    if projeto_validado:
        st.success(f"Squad/Projeto: {st.session_state['projeto_key']} — {st.session_state.get('projeto_name', '')}")

    # NOVA INTERFACE: Mostrar Sprint Atual e Recentes
    st.subheader("Selecione as Sprints")
    
    # Buscar sprints do board se projeto validado
    sprints_do_board = None
    if projeto_validado:
        try:
            # Usar board do session_state quando disponível (mais preciso)
            board_id_ctx = st.session_state.get('board_id')
            if board_id_ctx:
                from jiraproject.services.jira import buscar_sprints_do_board
                sprints_do_board = buscar_sprints_do_board(board_id_ctx)
            else:
                sprints_do_board = buscar_sprints_do_projeto_cache(projeto_validado)
            
            if sprints_do_board:
                # Mostrar Sprint Atual em destaque
                # Lista suspensa com sprint atual e 5 anteriores
                opcoes_sprint = []
                sprint_atual = None
                
                if sprints_do_board.get('ativa'):
                    sprint_atual = sprints_do_board['ativa']
                    st.success(f" Sprint Atual: {sprint_atual['nome']} (ID: {sprint_atual['id']}) - Estado: {sprint_atual.get('estado', 'Desconhecido')}")
                    
                    # Adicionar sprint atual
                    opcoes_sprint.append({
                        'id': sprint_atual['id'],
                        'nome': sprint_atual['nome'],
                        'label': f"{sprint_atual['nome']} (ID: {sprint_atual['id']}) - ATUAL",
                        'is_current': True
                    })
                
                # Adicionar 5 sprints anteriores
                if sprints_do_board.get('recentes'):
                    for sprint in sprints_do_board['recentes'][:5]:  # Apenas 5 anteriores
                        opcoes_sprint.append({
                            'id': sprint['id'],
                            'nome': sprint['nome'],
                            'label': f"{sprint['nome']} (ID: {sprint['id']})",
                            'is_current': False
                        })
                
                # Adicionar opção para múltiplas sprints
                if len(opcoes_sprint) > 1:
                    opcoes_sprint.append({
                        'id': 'multiple',
                        'nome': 'Múltiplas Sprints',
                        'label': f"Analisar Todas ({len(opcoes_sprint)} sprints)",
                        'is_current': False,
                        'is_multiple': True
                    })
                
                if opcoes_sprint:
                    st.divider()
                    st.subheader("Selecionar Sprint")
                    
                    # Selectbox retorna o próprio objeto da sprint (evita depender de label)
                    sprint_selecionada = st.selectbox(
                        "Escolha uma sprint para analisar:",
                        options=opcoes_sprint,
                        format_func=lambda o: o['label'],
                        key="sprint_escolhida_obj"
                    )
                    
                    if sprint_selecionada:
                        # Mostrar detalhes da sprint selecionada
                        col_info, col_botao = st.columns([2, 1])

                        with col_info:
                            if sprint_selecionada.get('is_multiple'):
                                # Opção de múltiplas sprints
                                st.info(f"**Selecionada:** Análise de Múltiplas Sprints ({len(opcoes_sprint)-1} sprints)")
                                st.caption("Inclui a sprint atual e as 5 anteriores")
                            elif sprint_selecionada['is_current']:
                                st.info(f" **Selecionada:** Sprint Atual - {sprint_selecionada['nome']}")
                            else:
                                st.info(f" **Selecionada:** {sprint_selecionada['nome']} (Sprint Anterior)")
                            
                        with col_botao:
                            # Botão removido; carregamento já é automático ao selecionar
                            pass
                
                st.divider()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível buscar sprints automaticamente: {str(e)[:100]}")
    
    
    # Carregamento automático ao selecionar Sprint: busca e popula o dash
    if projeto_validado:
        projeto_final = st.session_state['projeto']
        # Identificar seleção feita pelo selectbox
        sprint_ids_auto: list[int] = []
        # Usar o objeto selecionado diretamente, quando disponível
        sel_obj = st.session_state.get('sprint_escolhida_obj')
        if sel_obj and isinstance(sel_obj, dict):
            if sel_obj.get('is_multiple'):
                for op in opcoes_sprint:
                    if not op.get('is_multiple') and op['id'] != 'multiple':
                        sprint_ids_auto.append(int(op['id']))
            else:
                sprint_ids_auto.append(int(sel_obj['id']))
        # Se não houver seleção explícita, usar sprint atual se disponível
        if not sprint_ids_auto and sprints_do_board and sprints_do_board.get('ativa'):
            sprint_ids_auto = [int(sprints_do_board['ativa']['id'])]

        # Assinatura para evitar recarregar os mesmos dados incessantemente
        if sprint_ids_auto:
            signature = f"{projeto_final}|{','.join(map(str, sprint_ids_auto))}"
            # Sempre que a seleção mudar, limpar caches para evitar resíduos
            if st.session_state.get('last_selection_signature') != signature:
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
                try:
                    st.cache_resource.clear()
                except Exception:
                    pass
                st.session_state['last_selection_signature'] = signature
                st.session_state.pop('last_loaded_signature', None)
            # Recarregar ao mudar a assinatura efetiva de dados carregados
            if st.session_state.get('last_loaded_signature') != signature:
                with st.spinner("🔄 Carregando dados da(s) sprint(s)..."):
                    try:
                        dfs_sprints: list[pd.DataFrame] = []
                        sprints_com_erro: list[str] = []
                        sprints_sem_dados: list[int] = []
                        sprint_info: list[dict] = []
                        for sid in sprint_ids_auto:
                            try:
                                df_sprint = analisar_sprint(projeto_final, int(sid))
                                if not df_sprint.empty:
                                    df_sprint['Sprint ID'] = int(sid)
                                    df_sprint['Sprint Nome'] = df_sprint.attrs.get('sprint_nome', f'Sprint {sid}')
                                    dfs_sprints.append(df_sprint)
                                    sprint_info.append({
                                        'id': int(sid),
                                        'nome': df_sprint.attrs.get('sprint_nome', f'Sprint {sid}'),
                                        'inicio': df_sprint.attrs.get('sprint_inicio'),
                                        'fim': df_sprint.attrs.get('sprint_fim'),
                                        'total_itens': len(df_sprint),
                                    })
                                else:
                                    sprints_sem_dados.append(int(sid))
                            except Exception as e:
                                sprints_com_erro.append(f"Sprint {sid} ({str(e)[:40]}...)")
                        if dfs_sprints:
                            df_combinado = pd.concat(dfs_sprints, ignore_index=True)
                            st.session_state['df'] = df_combinado
                            st.session_state['projeto'] = projeto_final
                            st.session_state['sprints_selecionadas'] = sprint_ids_auto
                            st.session_state['sprint_info'] = sprint_info
                            st.session_state['total_sprint'] = len(df_combinado)
                            st.session_state['sprint_id'] = (
                                sprint_ids_auto[0] if len(sprint_ids_auto) == 1 else "Múltiplas"
                            )
                            st.session_state['sprint_nome'] = (
                                sprint_info[0]['nome'] if len(sprint_info) == 1 else f"{len(sprint_ids_auto)} Sprints"
                            )
                            st.session_state['sprint_inicio'] = sprint_info[0]['inicio'] if len(sprint_info) == 1 else None
                            st.session_state['sprint_fim'] = sprint_info[0]['fim'] if len(sprint_info) == 1 else None
                            st.session_state['last_loaded_signature'] = signature
                            # Atualizar sprint_id/nome exibidos (reflete a escolha atual)
                            st.session_state['sprint_id'] = (
                                sprint_ids_auto[0] if len(sprint_ids_auto) == 1 else "Múltiplas"
                            )
                            if sprints_com_erro or sprints_sem_dados:
                                avisos: list[str] = []
                                if sprints_com_erro:
                                    avisos.extend(sprints_com_erro)
                                if sprints_sem_dados:
                                    avisos.extend([f"Sprint {sid} (sem issues)" for sid in sprints_sem_dados])
                                st.warning("⚠️ " + ", ".join(avisos))
                        else:
                            st.info("Sem dados para a(s) sprint(s) selecionada(s).")
                    except Exception as e:
                        st.error(f"❌ Erro ao carregar dados automaticamente: {str(e)}")
    

# Título principal e subtítulo (resiliente a mudanças/seleções)
projeto_display = st.session_state.get('projeto') or st.session_state.get('projeto_key') or 'N/A'
sprint_display = None

# Lógica para determinar o título da sprint baseado no estado atual
if 'df' in st.session_state and isinstance(st.session_state.get('df'), pd.DataFrame) and not st.session_state['df'].empty:
    # Preferir informações vindas dos atributos do df
    sprint_nome = st.session_state['df'].attrs.get('sprint_nome', f"Sprint {st.session_state.get('sprint_id', 'N/A')}")
    sprint_inicio = st.session_state['df'].attrs.get('sprint_inicio')
    sprint_fim = st.session_state['df'].attrs.get('sprint_fim')
    periodo_texto = ""
    if sprint_inicio and sprint_fim:
        try:
            from datetime import datetime
            inicio_dt = datetime.fromisoformat(sprint_inicio.replace('Z', '+00:00'))
            fim_dt = datetime.fromisoformat(sprint_fim.replace('Z', '+00:00'))
            periodo_texto = f" ({inicio_dt.strftime('%d/%m/%Y')} - {fim_dt.strftime('%d/%m/%Y')})"
        except Exception:
            periodo_texto = ""
    sprint_display = f"{sprint_nome}{periodo_texto}"
elif st.session_state.get('sprint_info'):
    info_list = st.session_state.get('sprint_info') or []
    if isinstance(info_list, list) and len(info_list) > 0:
        if len(info_list) == 1:
            sprint_display = info_list[0].get('nome') or f"Sprint {info_list[0].get('id', '')}"
        else:
            sprint_display = f"{len(info_list)} Sprints selecionadas"
elif st.session_state.get('sprint_escolhida_obj'):
    # Fallback imediato: label escolhido no select (antes do carregamento do df)
    sprint_obj = st.session_state.get('sprint_escolhida_obj')
    if sprint_obj and isinstance(sprint_obj, dict):
        if sprint_obj.get('is_multiple'):
            sprint_display = "Múltiplas Sprints"
        else:
            sprint_display = sprint_obj.get('nome', sprint_obj.get('label', f"Sprint {sprint_obj.get('id', 'N/A')}"))

st.markdown('<h1 class="main-header">🎯 Dashboard de Análise de Sprint Jira</h1>', unsafe_allow_html=True)
if projeto_display or sprint_display:
    st.markdown(
        f"<p style='text-align:center; margin-top:-1rem;'>Squad/Projeto: <strong>{projeto_display}</strong>" +
        (f" &nbsp;|&nbsp; Sprint: <strong>{sprint_display}</strong>" if sprint_display else "") +
        "</p>",
        unsafe_allow_html=True,
    )

# Conteúdo principal
if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    projeto = st.session_state.get('projeto', 'N/A')
    sprint_id = st.session_state.get('sprint_id', 'N/A')
    total_sprint = st.session_state.get('total_sprint', len(df))
    
    # Tabs para diferentes visualizações, condicionadas ao modelo de trabalho
    if st.session_state.get('modelo_trabalho', 'Scrum') == 'Kanban':
        (tab7,) = st.tabs(["Kanban"])
    else:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Visão Geral",
            "Análise por Responsável",
            "Dados Detalhados",
            "Tempo de Conclusão",
            "Bugs & Impedimentos",
            "Story Points",
        ])
    
    # Renderização das abas Scrum somente quando modelo != Kanban
    if st.session_state.get('modelo_trabalho', 'Scrum') != 'Kanban':
        with tab1:
            st.subheader("Visão Executiva da Sprint")

            # === SEÇÃO 1: CONTADOR SUMARIZADO ===
            st.subheader("Resumo Executivo")

            # Filtrar apenas itens de interesse usando tipo canônico
            tipos_interesse = {'História', 'Débito Técnico', 'Spike', 'Bug', 'Impedimento'}
            df_tmp_tipos = df.copy()
            df_tmp_tipos['TipoCanon'] = df_tmp_tipos['Tipo de Item'].apply(lambda x: canonical_type(normalize(x)))
            df_exec = df_tmp_tipos[df_tmp_tipos['TipoCanon'].isin(tipos_interesse)]

            # Contadores por tipo (canônico)
            contador_tipos = df_exec['TipoCanon'].value_counts()
            total_itens_exec = len(df_exec)

            # Métricas em cards
            col1, col2, col3, col4, col5, col6 = st.columns(6)

            with col1:
                metric("Total Itens", total_itens_exec, help_text="Total de itens ágeis na sprint")

            with col2:
                historias = contador_tipos.get('História', 0)
                pct_hist = (historias / total_itens_exec * 100) if total_itens_exec > 0 else 0
                metric("Histórias", historias, delta=pct_delta(historias, total_itens_exec), help_text="Histórias de usuário")

            with col3:
                debitos = contador_tipos.get('Débito Técnico', 0)
                pct_debt = (debitos / total_itens_exec * 100) if total_itens_exec > 0 else 0
                metric("🔧 Débitos", debitos, delta=pct_delta(debitos, total_itens_exec), help_text="Débitos técnicos")

            with col4:
                spikes = contador_tipos.get('Spike', 0)
                pct_spike = (spikes / total_itens_exec * 100) if total_itens_exec > 0 else 0
                metric("Spikes", spikes, delta=pct_delta(spikes, total_itens_exec), help_text="Investigações e spikes")

            with col5:
                bugs = contador_tipos.get('Bug', 0)
                pct_bug = (bugs / total_itens_exec * 100) if total_itens_exec > 0 else 0
                metric("Bugs", bugs, delta=pct_delta(bugs, total_itens_exec), help_text="Correções de bugs")

            with col6:
                imped = contador_tipos.get('Impedimento', 0)
                pct_imp = (imped / total_itens_exec * 100) if total_itens_exec > 0 else 0
                metric("Impedimentos", imped, delta=pct_delta(imped, total_itens_exec), help_text="Itens impedidos")

            st.markdown("---")

            # === SEÇÃO 2: DISTRIBUIÇÕES (sem tabela detalhada) ===
            st.subheader("Distribuições")

            if not df_exec.empty:
                col1, col2 = st.columns(2)

                with col1:
                    # Distribuição por status
                    status_counts = df_exec['Status'].value_counts()

                    # Definir cores do Jira por status
                    # Criar lista de cores para cada status
                    colors = [status_color(status) for status in status_counts.index]

                    from jiraproject.utils.ui import status_bar_figure
                    fig_status_exec = status_bar_figure(status_counts.to_dict())

                    # Adicionar quantidades no meio das barras
                    fig_status_exec.update_traces(
                        texttemplate='%{y}',
                        textposition='inside',
                        textfont_size=12,
                        textfont_color='white'
                    )

                    fig_status_exec.update_layout(
                        showlegend=False,
                        xaxis_tickangle=-45
                    )

                    st.plotly_chart(fig_status_exec, use_container_width=True)

                with col2:
                    # Gráfico de pizza: % de Histórias, Débitos e Bugs
                    st.subheader("Resumo por Tipo (% Histórias, Débitos, Bugs)")
                    historias_qtd = contador_tipos.get('História', 0)
                    debitos_qtd = contador_tipos.get('Débito Técnico', 0)
                    bugs_qtd = contador_tipos.get('Bug', 0)
                    valores = [historias_qtd, debitos_qtd, bugs_qtd]
                    nomes = ['História', 'Débito Técnico', 'Bug']
                    if sum(valores) > 0:
                        # Usando ChartFactory para gráfico padronizado
                        fig_pizza_tipo = ChartFactory.create_pie_chart(
                            values=valores, 
                            names=nomes,
                            title="Resumo por Tipo"
                        )
                        st.plotly_chart(fig_pizza_tipo, use_container_width=True)
                    else:
                        st.info("Sem dados de Histórias/Débitos para exibir")
            else:
                st.warning("⚠️ Nenhum item ágil encontrado na sprint.")

    if st.session_state.get('modelo_trabalho', 'Scrum') == 'Kanban':
        # Aba: Kanban (métricas de fluxo)
        with tab7:
            st.subheader("Métricas Kanban")
            # Garantir colunas necessárias
            possui_datas = ('Data Criação' in df.columns) and ('Data Resolução' in df.columns)
            if not possui_datas:
                st.info("⚠️ Esta aba requer as colunas 'Data Criação' e 'Data Resolução'. Carregue dados que incluam datas.")
            else:
                # Lead time (Criação -> Resolução)
                df_lt = calc_resolution_days(df.copy())
                df_resolvidos_lt = get_resolved_items(df_lt)
                # Calcular estatísticas de uma vez
                time_stats = calculate_time_statistics(df_lt)
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    metric("Itens Resolvidos", time_stats['count'])
                with col_m2:
                    metric("Lead time médio", f"{time_stats['mean']:.1f}" if time_stats['mean'] is not None else "N/A")
                with col_m3:
                    metric("Mediana", f"{time_stats['median']:.1f}" if time_stats['median'] is not None else "N/A")
                with col_m4:
                    metric("SLE (p85)", f"{time_stats['p85']:.1f}" if time_stats['p85'] is not None else "N/A")

                st.subheader("Distribuição de Lead time")
                if not df_resolvidos_lt.empty:
                    fig_hist = px.histogram(df_resolvidos_lt, x='Dias para Resolução', nbins=20, title='Histograma de Lead time (dias)')
                    st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.info("Sem itens resolvidos para exibir distribuição.")

                st.markdown("---")
                # Throughput semanal
                st.subheader("Throughput semanal (itens resolvidos)")
                df_tp = df[df['Data Resolução'].notna()].copy()
                if not df_tp.empty:
                    df_tp['Semana'] = pd.to_datetime(df_tp['Data Resolução'], errors='coerce').dt.to_period('W').astype(str)
                    tp_semana = df_tp.groupby('Semana').size().reset_index(name='Itens Resolvidos')
                    fig_tp = bar(tp_semana, x='Semana', y='Itens Resolvidos', title='Throughput por semana', color='Semana')
                    fig_tp.update_layout(showlegend=False, xaxis_tickangle=-45)
                    st.plotly_chart(fig_tp, use_container_width=True)
                else:
                    st.info("Sem resoluções no período carregado.")

                st.markdown("---")
                # Arrival vs Departure semanal
                st.subheader("Chegada vs Saída (semanal)")
                df_arr = df[df['Data Criação'].notna()].copy()
                df_dep = df[df['Data Resolução'].notna()].copy()
                if not df_arr.empty or not df_dep.empty:
                    if not df_arr.empty:
                        df_arr['Semana'] = pd.to_datetime(df_arr['Data Criação'], errors='coerce').dt.to_period('W').astype(str)
                        arr = df_arr.groupby('Semana').size().reset_index(name='Criados')
                    else:
                        arr = pd.DataFrame(columns=['Semana', 'Criados'])
                    if not df_dep.empty:
                        df_dep['Semana'] = pd.to_datetime(df_dep['Data Resolução'], errors='coerce').dt.to_period('W').astype(str)
                        dep = df_dep.groupby('Semana').size().reset_index(name='Concluídos')
                    else:
                        dep = pd.DataFrame(columns=['Semana', 'Concluídos'])
                    fluxo = pd.merge(arr, dep, on='Semana', how='outer').fillna(0)
                    fluxo_melt = fluxo.melt(id_vars='Semana', value_vars=['Criados', 'Concluídos'], var_name='Tipo', value_name='Quantidade')
                    fig_fluxo = px.bar(fluxo_melt, x='Semana', y='Quantidade', color='Tipo', barmode='group', title='Chegada vs Saída (semanal)')
                    fig_fluxo.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_fluxo, use_container_width=True)
                else:
                    st.info("Sem dados de criação ou conclusão para exibir fluxo semanal.")

                st.markdown("---")
                # WIP atual e idade de WIP
                st.subheader("WIP atual e Idade do WIP")
                status_prog = {s.lower() for s in config.STATUS_EM_PROGRESSO}
                def is_prog(s):
                    return isinstance(s, str) and s.lower() in status_prog
                df_wip = df[(df['Status'].apply(is_prog)) & (df['Data Resolução'].isna())].copy()
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    metric("WIP atual", len(df_wip))
                with col_w2:
                    if not df_wip.empty:
                        agora = pd.Timestamp(datetime.now())
                        criacoes = pd.to_datetime(df_wip['Data Criação'], errors='coerce')
                        if getattr(criacoes.dt, 'tz', None) is not None:
                            criacoes = criacoes.dt.tz_localize(None)
                        idade = (agora.tz_localize(None) if getattr(agora, 'tz', None) is not None else agora) - criacoes
                        idade_dias = (idade.dt.total_seconds() / 86400.0).round(1)
                        media_idade = idade_dias.mean()
                        metric("Idade média do WIP (dias)", f"{media_idade:.1f}" if pd.notna(media_idade) else "N/A")
                    else:
                        metric("Idade média do WIP (dias)", "N/A")

                st.markdown("---")
                # Mix de trabalho
                st.subheader("Mix de trabalho (por tipo)")
                tipo_counts = df['Tipo de Item'].value_counts()
                if not tipo_counts.empty:
                    fig_mix = pie(values=tipo_counts.values, names=tipo_counts.index, title='Composição por Tipo')
                    st.plotly_chart(fig_mix, use_container_width=True)
                else:
                    st.info("Sem dados de tipo para exibir mix.")

                st.markdown("---")
                # Lead time por tipo
                st.subheader("Lead time por Tipo (média em dias)")
                lt_tipo = group_by_time_stats(df_lt, 'Tipo de Item')
                
                if not lt_tipo.empty:
                    fig_lt_tipo = bar(lt_tipo, x='Tipo de Item', y='Média Dias', title='Lead time médio por Tipo', color='Tipo de Item')
                    fig_lt_tipo.update_layout(showlegend=False, xaxis_tickangle=-45)
                    st.plotly_chart(fig_lt_tipo, use_container_width=True)
                else:
                    st.info("Sem itens resolvidos para calcular lead time por tipo.")

                st.markdown("---")
                # Taxa de defeitos (bugs concluídos / concluídos)
                st.subheader("Taxa de defeitos")
                if not df_tp.empty:
                    bugs_conc = df_tp['Tipo de Item'].str.contains('Bug', case=False, na=False).sum()
                    taxa_defeitos = (bugs_conc / len(df_tp) * 100.0) if len(df_tp) > 0 else 0.0
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        metric("Bugs concluídos", bugs_conc)
                    with col_d2:
                        metric("% Bugs sobre concluídos", f"{taxa_defeitos:.1f}%")
                else:
                    st.info("Sem itens concluídos para calcular taxa de defeitos.")

    
    if st.session_state.get('modelo_trabalho', 'Scrum') != 'Kanban':
        with tab2:
            st.subheader("👥 Análise Detalhada por Responsável")

            # Seletor de responsável
            responsaveis = ['👥 Visão Geral'] + sorted([r for r in df['Responsável'].unique() if pd.notna(r)])
            responsavel_selecionado = st.selectbox(
                "Selecione um responsável para análise detalhada:",
                options=responsaveis,
                index=0
            )

            if responsavel_selecionado == '👥 Visão Geral':
                # Resumo de todos os responsáveis
                st.subheader("Resumo de Todos os Responsáveis")

                # Calcular dias para resolução para cada item
                df_calc = df.copy()
                df_calc['Dias para Resolução'] = 0  # valor padrão

                # Calcular apenas para itens que têm ambas as datas
                mask_datas = df_calc['Data Criação'].notna() & df_calc['Data Resolução'].notna()
                if mask_datas.any():
                    df_calc.loc[mask_datas, 'Dias para Resolução'] = (
                        pd.to_datetime(df_calc.loc[mask_datas, 'Data Resolução']) - 
                        pd.to_datetime(df_calc.loc[mask_datas, 'Data Criação'])
                    ).dt.days

                df_calc = calc_dias(df_calc, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')
                resumo_responsaveis = df_calc.groupby('Responsável').agg({
                    'Chave': 'count',
                    'Dias para Resolução': 'mean'
                }).rename(columns={'Chave': 'Total_Itens'}).reset_index()

                # Adicionar percentuais e arredondar dias
                resumo_responsaveis['%'] = (resumo_responsaveis['Total_Itens'] / len(df) * 100).round(1)
                resumo_responsaveis['Dias para Resolução'] = resumo_responsaveis['Dias para Resolução'].round(1)

                # Ordenar por total de itens
                resumo_responsaveis = resumo_responsaveis.sort_values('Total_Itens', ascending=False)

                # Gráfico de barras - itens por responsável
                fig_resp_items = bar(resumo_responsaveis, x='Responsável', y='Total_Itens', title=None, color='Responsável')
                fig_resp_items.update_layout(xaxis_tickangle=-45, showlegend=False)
                st.plotly_chart(fig_resp_items, use_container_width=True)

                # Tabela resumo
                show_df(resumo_responsaveis, use_container_width=True, hide_index=True)

            else:
                # Análise individual do responsável
                df_resp = df[df['Responsável'] == responsavel_selecionado]

                if not df_resp.empty:
                    # Calcular dias para resolução antes de usar
                    df_resp = df_resp.copy()
                    df_resp['Dias para Resolução'] = 0  # valor padrão

                    df_resp = calc_dias(df_resp, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')

                    # Métricas do responsável
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        metric("Total de Itens", len(df_resp))

                    with col2:
                        # Calcular dias médios para resolução do responsável
                        dias_resp = df_resp['Dias para Resolução'].mean()
                        metric("Dias Médios", f"{dias_resp:.1f}")

                    with col3:
                        tipos_resp = df_resp['Tipo de Item'].nunique()
                        metric("Tipos Diferentes", tipos_resp)

                    with col4:
                        pct_total = (len(df_resp) / len(df) * 100)
                        metric("% da Sprint", f"{pct_total:.1f}%")

                    # Gráficos do responsável
                    col1, col2 = st.columns(2)

                    with col1:
                        # Distribuição por tipo
                        tipo_resp_counts = df_resp['Tipo de Item'].value_counts()

                        fig_tipo_resp = pie(values=tipo_resp_counts.values, names=tipo_resp_counts.index, title=f'Tipos de Item - {responsavel_selecionado}')
                        st.plotly_chart(fig_tipo_resp, use_container_width=True)

                    with col2:
                        # Distribuição por status
                        status_resp_counts = df_resp['Status'].value_counts()
                        fig_status_resp = bar(
                            df=None,
                            x=status_resp_counts.index,
                            y=status_resp_counts.values,
                            title=f'Status dos Itens - {responsavel_selecionado}',
                            color=status_resp_counts.index,
                        )
                        fig_status_resp.update_layout(xaxis_tickangle=-45, showlegend=False)
                        st.plotly_chart(fig_status_resp, use_container_width=True)

                    # Lista de itens do responsável
                    st.subheader(f"🎫 Itens de {responsavel_selecionado}")

                    # Preparar dados com dias para resolução
                    df_resp_exibir = df_resp.copy()
                    df_resp_exibir['Dias para Resolução'] = 0  # valor padrão

                    df_resp_exibir = calc_dias(df_resp_exibir, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')

                    colunas_exibir = ['Chave', 'Resumo', 'Tipo de Item', 'Status', 'Dias para Resolução']
                    df_resp_final = df_resp_exibir[colunas_exibir].copy()

                    show_df(df_resp_final, use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum item encontrado para este responsável.")
    
    if st.session_state.get('modelo_trabalho', 'Scrum') != 'Kanban':
        with tab3:
            st.subheader("📋 Dados Detalhados da Sprint")

            # Calcular dias para resolução para estatísticas de tempo
            df_with_days = calc_dias(df.copy(), 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')
            
            # Estatísticas de Tempo
            if 'Dias para Resolução' in df_with_days.columns:
                st.subheader("⏱️ Estatísticas de Tempo")
                tempo_stats_metrics(df_with_days, 'Dias para Resolução')
                st.markdown("---")

            # Filtros usando componentes reutilizáveis
            st.subheader("🔍 Filtros")
            col_filtro1, col_filtro2 = st.columns(2)

            with col_filtro1:
                tipos_selecionados = FilterComponents.tipo_item_filter(
                    df, key_suffix="dados_detalhados"
                )

            with col_filtro2:
                sprints_filtro = FilterComponents.sprint_filter(
                    df, key_suffix="dados_detalhados"
                )

            # Aplicar filtros usando função centralizada
            df_filtrado = apply_filters(
                df, 
                tipo_filter=tipos_selecionados,
                sprint_filter=sprints_filtro
            )

            # Calcular "Dias para Resolução" e remover colunas de data originais
            df_filtrado = calc_dias(df_filtrado, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')

            # Garantir que a coluna seja numérica para evitar ArrowTypeError
            if 'Dias para Resolução' in df_filtrado.columns:
                df_filtrado['Dias para Resolução'] = pd.to_numeric(df_filtrado['Dias para Resolução'], errors='coerce')

            # Remover as colunas de data originais
            colunas_para_remover = ['Data Criação', 'Data Resolução']
            for coluna in colunas_para_remover:
                if coluna in df_filtrado.columns:
                    df_filtrado = df_filtrado.drop(columns=[coluna])

            # Mostrar resumo dos filtros aplicados
            filters_applied = []
            if tipos_selecionados and 'Todos' not in tipos_selecionados:
                filters_applied.append(f"Tipos: {len(tipos_selecionados)}")
            if sprints_filtro and 'Todas' not in sprints_filtro:
                filters_applied.append(f"Sprints: {len(sprints_filtro)}")
            
            show_filter_summary(len(df), len(df_filtrado), filters_applied)

            # Controles de exibição
            st.subheader("⚙️ Configurações de Exibição")
            col_cfg1, col_cfg2 = st.columns(2)

            # Filtro adicional por Tipo de Item (aplicado apenas na exibição)
            with col_cfg1:
                tipos_disp_cfg = sorted(df_filtrado['Tipo de Item'].dropna().unique().tolist())
                tipos_exibicao = st.multiselect(
                    "Filtro por Tipo de Item",
                    options=tipos_disp_cfg,
                    default=[],
                    help="Filtrar os registros exibidos por Tipo de Item"
                )

            # Aplicar filtro adicional de exibição
            df_exib_src = df_filtrado.copy()
            if tipos_exibicao:
                df_exib_src = df_exib_src[df_exib_src['Tipo de Item'].isin(tipos_exibicao)]

            # Seleção de colunas usando componente reutilizável
            with col_cfg2:
                # Definir colunas padrão (principais)
                colunas_principais = ['Chave', 'Resumo', 'Tipo de Item', 'Status', 'Responsável', 'Dias para Resolução']
                # Adicionar 'Sprint Nome' quando disponível
                if 'Sprint Nome' in df_exib_src.columns:
                    colunas_principais.insert(-1, 'Sprint Nome')  # Antes de 'Dias para Resolução'

                colunas_selecionadas = FilterComponents.column_selector(
                    df_exib_src,
                    default_columns=colunas_principais,
                    key_suffix="dados_detalhados",
                    exclude_columns=['Sprint ID']  # Excluir Sprint ID da lista
                )

            # Aplicar configurações
            if colunas_selecionadas:
                df_exibir = df_exib_src[colunas_selecionadas]

                # Exibir dataframe
                show_df(df_exibir, use_container_width=True, hide_index=True, height=600)

                # Botão de download
                csv = df_exibir.to_csv(index=False)
                filename = f"{projeto}_{sprint_id}_dados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

                st.download_button(
                    label="📥 Download dos Dados (CSV)",
                    data=csv,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ Selecione pelo menos uma coluna para exibir")
    
    if st.session_state.get('modelo_trabalho', 'Scrum') != 'Kanban':
        with tab4:
            st.subheader("⏱️ Análise de Tempo de Conclusão")

            # Verificar se as colunas de data existem
            if 'Data Criação' not in df.columns or 'Data Resolução' not in df.columns:
                st.warning("⚠️ Dados de tempo não disponíveis. As colunas 'Data Criação' e 'Data Resolução' não foram encontradas.")
                st.info("💡 Esta funcionalidade requer que as informações de data estejam presentes.")
            else:
                # Filtrar itens com datas válidas (independente de Story Points)
                df_tempo = df.copy()
                df_tempo = df_tempo.dropna(subset=['Data Criação', 'Data Resolução'])
            
            if df_tempo.empty:
                st.warning("❌ Nenhum item com datas válidas encontrado.")
            else:
                # Calcular dias para conclusão
                df_tempo['Dias para Conclusão'] = (pd.to_datetime(df_tempo['Data Resolução']) - pd.to_datetime(df_tempo['Data Criação'])).dt.days
                
                # Métricas principais
                st.subheader("📊 Estatísticas Gerais")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    metric("🎫 Total de Itens", len(df_tempo))
                
                with col2:
                    media_dias = df_tempo['Dias para Conclusão'].mean()
                    metric("📅 Média de Dias", f"{media_dias:.1f}")
                
                with col3:
                    min_dias = df_tempo['Dias para Conclusão'].min()
                    metric("🚀 Mínimo", f"{min_dias} dias")
                
                with col4:
                    max_dias = df_tempo['Dias para Conclusão'].max()
                    metric("🐌 Máximo", f"{max_dias} dias")
                
                # Análise por tipo de item
                st.subheader("⏱Tempo Médio por Tipo de Item")
                tipos_ageis = TIPOS_AGEIS_CANON + ['Bug']
                df_tipos = df_tempo[df_tempo['Tipo de Item'].apply(lambda x: canonical_type(normalize(x)) in tipos_ageis)]
                
                if not df_tipos.empty:
                    medias_por_tipo = df_tipos.groupby('Tipo de Item')['Dias para Conclusão'].agg(['mean', 'count']).reset_index()
                    medias_por_tipo.columns = ['Tipo de Item', 'Média de Dias', 'Quantidade']
                    medias_por_tipo['Média de Dias'] = medias_por_tipo['Média de Dias'].round(1)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_medias = bar(
                            medias_por_tipo,
                            x='Tipo de Item',
                            y='Média de Dias',
                            title='Dias Médios para Conclusão por Tipo',
                            color='Tipo de Item'
                        )
                        fig_medias.update_layout(showlegend=False)
                        st.plotly_chart(fig_medias, use_container_width=True)
                    
                    with col2:
                        show_df(medias_por_tipo, use_container_width=True, hide_index=True)
                
                # Scatter plot: Story Points vs Dias
                st.subheader(" Relação entre Story Points e Tempo de Conclusão")
                fig_scatter = scatter(
                    df_tempo,
                    x='Story Points',
                    y='Dias para Conclusão',
                    color='Tipo de Item',
                    size='Story Points',
                    hover_data=['Chave', 'Resumo', 'Responsável'],
                    title='Relação entre Story Points e Tempo de Conclusão'
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Tabela detalhada
                st.subheader("🎫 Dados Detalhados")
                df_exibir_tempo = df_tempo[['Chave', 'Tipo de Item', 'Resumo', 'Responsável', 'Story Points', 'Dias para Conclusão']].sort_values('Dias para Conclusão', ascending=False)
                show_df(df_exibir_tempo, use_container_width=True, hide_index=True)

    if st.session_state.get('modelo_trabalho', 'Scrum') != 'Kanban':
        with tab5:
            st.subheader("Bugs & Impedimentos")

            # Filtrar por issuetype apenas: Bug e Impedimento
            df_bugs = df[df['Tipo de Item'].str.fullmatch(r"(?i)bug", na=False)]
            df_impedimentos_tipo = df[df['Tipo de Item'].str.contains('Impedimento', case=False, na=False)]

            # Combinar bugs e impedimentos (por issuetype), removendo duplicatas
            df_bugs_impedimentos = pd.concat([df_bugs, df_impedimentos_tipo]).drop_duplicates()
            df_bugs_impedimentos['Categoria'] = df_bugs_impedimentos['Tipo de Item'].apply(
                lambda t: 'Bug' if (isinstance(t, str) and t.strip().lower() == 'bug') else 'Impedimento'
            )

            if not df_bugs_impedimentos.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    metric("Total de Bugs", len(df_bugs))
                with col2:
                    metric("Impedimentos", len(df_impedimentos_tipo))
                with col3:
                    metric("Total Geral", len(df_bugs_impedimentos))

                st.markdown("---")
                st.subheader("Tabela de Impedimentos")
                df_impedimentos_table = df_bugs_impedimentos.copy()
                df_impedimentos_table['Tempo Total (dias)'] = 0
                mask_datas = (df_impedimentos_table['Data Criação'].notna() & df_impedimentos_table['Data Resolução'].notna())
                if mask_datas.any():
                    df_impedimentos_table.loc[mask_datas, 'Tempo Total (dias)'] = (
                        pd.to_datetime(df_impedimentos_table.loc[mask_datas, 'Data Resolução']) - 
                        pd.to_datetime(df_impedimentos_table.loc[mask_datas, 'Data Criação'])
                    ).dt.days
                    mask_nao_resolvido = (df_impedimentos_table['Data Criação'].notna() & df_impedimentos_table['Data Resolução'].isna())
                    if mask_nao_resolvido.any():
                        agora = pd.Timestamp(datetime.now())
                        datas_criacao = pd.to_datetime(df_impedimentos_table.loc[mask_nao_resolvido, 'Data Criação'])
                        if agora.tz is not None:
                            agora = agora.tz_localize(None)
                        if hasattr(datas_criacao.dtype, 'tz') and datas_criacao.dtype.tz is not None:
                            datas_criacao = datas_criacao.dt.tz_localize(None)
                        df_impedimentos_table.loc[mask_nao_resolvido, 'Tempo Total (dias)'] = (
                            agora - datas_criacao
                        ).dt.days

                colunas_tabela = {
                    'Chave': 'Chave',
                    'Resumo': 'Resumo', 
                    'Status': 'Status',
                    'Responsável': 'Agente Causador',
                    'Tempo Total (dias)': 'Tempo Total (dias)'
                }
                df_tabela_final = df_impedimentos_table[list(colunas_tabela.keys())].rename(columns=colunas_tabela)
                df_tabela_final = df_tabela_final.sort_values('Tempo Total (dias)', ascending=False)
                colunas_finais = ['Chave', 'Resumo', 'Status', 'Agente Causador', 'Tempo Total (dias)']
                df_tabela_final = df_tabela_final[colunas_finais]
                show_df(df_tabela_final, use_container_width=True, hide_index=True, height=400, column_config=build_column_config(colunas_finais))

                st.subheader("Análise de Bugs & Impedimentos")
                col1, col2 = st.columns(2)
                with col1:
                    cat_counts = df_bugs_impedimentos['Categoria'].value_counts()
                    fig_tipos = pie(values=cat_counts.values, names=cat_counts.index, title="Distribuição por Categoria", color_sequence=['#dc3545', '#ffc107'])
                    st.plotly_chart(fig_tipos, use_container_width=True)
                with col2:
                    if 'Tempo Total (dias)' in df_impedimentos_table.columns:
                        df_tmp_tempo = df_impedimentos_table.copy()
                        df_tmp_tempo['Categoria'] = df_tmp_tempo['Tipo de Item'].apply(
                            lambda t: 'Bug' if (isinstance(t, str) and 'bug' in t.lower()) else 'Impedimento'
                        )
                        tempo_medio = df_tmp_tempo.groupby('Categoria')['Tempo Total (dias)'].mean().reset_index()
                        tempo_medio.columns = ['Tipo', 'Tempo Médio (dias)']
                        tempo_medio['Tempo Médio (dias)'] = tempo_medio['Tempo Médio (dias)'].round(1)
                        if not tempo_medio.empty:
                            fig_tempo = bar(tempo_medio, x='Tipo', y='Tempo Médio (dias)', title="Tempo Médio por Tipo", color='Tipo', color_map={'Bug': '#dc3545', 'Impedimento': '#ffc107'})
                            fig_tempo.update_layout(showlegend=False)
                            st.plotly_chart(fig_tempo, use_container_width=True)
                        else:
                            st.info("⏱️ Dados de tempo não disponíveis para análise")
            else:
                st.info("✅ Nenhum bug ou impedimento encontrado nesta sprint!")
                st.markdown("### 🎉 Excelente!")
                st.markdown("- Não há bugs registrados")
                st.markdown("- Não há itens com status de impedimento")
                st.markdown("- A sprint está seguindo sem bloqueios identificados")
    
    # Início do bloco da Aba Story Points
    if st.session_state.get('modelo_trabalho', 'Scrum') != 'Kanban':
        with tab6:
            st.subheader("Análise de Story Points")

            # Normalizar tipos (sem acentos) para filtrar com segurança
            tipos_validos_norm = {normalize('História'), normalize('Débito Técnico'), normalize('Spike')}
            mask_tipos = df['Tipo de Item'].apply(lambda x: normalize(x) in tipos_validos_norm)
            df_story_points = df[mask_tipos & (df['Story Points'] > 0)].copy()
            st.write(f"Itens com Story Points (Histórias/Débitos/Spikes): {len(df_story_points)}")
        
            if df_story_points.empty:
                st.error("❌ Nenhum item com Story Points > 0 encontrado nas sprints selecionadas.")
                st.info("💡 Verifique se os itens possuem Story Points preenchidos no Jira.")
            else:
                # Calcular dias para resolução
                df_story_points = calc_dias(df_story_points, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')
            
            # === SEÇÃO 1: FILTROS ===
            st.subheader("Filtros")
            col_filtro1, col_filtro2 = st.columns(2)
            
            with col_filtro1:
                # Filtro por data
                data_inicio = st.date_input(
                    "Data de Criação - A partir de:",
                    value=df_story_points['Data Criação'].min().date() if df_story_points['Data Criação'].notna().any() else datetime.now().date(),
                    help="Filtrar itens criados a partir desta data"
                )
                
            with col_filtro2:
                data_resolucao_fim = st.date_input(
                    "Data de Resolução - Até:",
                    value=(
                        df_story_points['Data Resolução'].dropna().max().date()
                        if df_story_points['Data Resolução'].notna().any()
                        else datetime.now().date()
                    ),
                    help="Filtrar itens resolvidos até esta data"
                )
            
            # Aplicar filtro por data
            df_filtrado_sp = df_story_points.copy()
            if data_inicio:
                df_filtrado_sp = df_filtrado_sp[df_filtrado_sp['Data Criação'].dt.date >= data_inicio]
            if data_resolucao_fim:
                # Manter somente itens com data de resolução disponível e dentro do limite
                df_filtrado_sp = df_filtrado_sp[df_filtrado_sp['Data Resolução'].notna()]
                df_filtrado_sp = df_filtrado_sp[df_filtrado_sp['Data Resolução'].dt.date <= data_resolucao_fim]
            
            # === MODO HISTÓRICO (IGNORAR SPRINTS) ===
            st.markdown("---")
            usar_historico = st.checkbox("Usar modo histórico por período (ignora sprints selecionadas)", value=False)
            if usar_historico:
                proj_key = st.session_state.get('projeto_key') or st.session_state.get('projeto')
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hist_inicio = st.date_input("Histórico - Criados a partir de:", value=data_inicio)
                with col_h2:
                    hist_fim = st.date_input("Histórico - Criados até:", value=data_resolucao_fim)
                if proj_key and hist_inicio and hist_fim:
                    from jiraproject.services import jira as jira_service
                    issues = jira_service.buscar_issues_por_periodo(
                        proj_key,
                        hist_inicio.strftime('%Y-%m-%d'),
                        hist_fim.strftime('%Y-%m-%d')
                    )
                    # Converter issues em DataFrame compatível
                    linhas = []
                    for it in issues:
                        f = it.get('fields', {})
                        tipo = (f.get('issuetype', {}) or {}).get('name')
                        resumo = f.get('summary')
                        chave = it.get('key')
                        status = (f.get('status', {}) or {}).get('name')
                        assignee = (f.get('assignee', {}) or {}).get('displayName')
                        created = f.get('created')
                        resolutiondate = f.get('resolved') or f.get('resolutiondate')
                        # Story Points: tentar campos comuns
                        sp = (
                            f.get('customfield_10016') or f.get('customfield_10026') or f.get('customfield_10031') or f.get('customfield_10010')
                        )
                        try:
                            sp = float(sp) if sp is not None else 0.0
                        except Exception:
                            sp = 0.0
                        linhas.append({
                            'Chave': chave,
                            'Resumo': resumo,
                            'Tipo de Item': tipo,
                            'Status': status,
                            'Responsável': assignee,
                            'Data Criação': pd.to_datetime(created) if created else pd.NaT,
                            'Data Resolução': pd.to_datetime(resolutiondate) if resolutiondate else pd.NaT,
                            'Story Points': sp
                        })
                    df_hist = pd.DataFrame(linhas)
                    # Se não houver dados, evitar KeyError e seguir com vazio
                    if df_hist.empty:
                        st.info("Sem dados históricos para o período selecionado.")
                        df_story_points = pd.DataFrame(columns=['Chave','Resumo','Tipo de Item','Status','Responsável','Data Criação','Data Resolução','Story Points','Dias para Resolução'])
                        df_filtrado_sp = df_story_points.copy()
                    else:
                        # Aplicar filtros e cálculo sobre histórico
                        mask_tipos_hist = df_hist['Tipo de Item'].apply(lambda x: normalize(x) in tipos_validos_norm)
                        df_story_points = df_hist[mask_tipos_hist & (df_hist['Story Points'] > 0)].copy()
                        df_story_points = calc_dias(df_story_points, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')
                        df_filtrado_sp = df_story_points.copy()
                        df_filtrado_sp = df_filtrado_sp[df_filtrado_sp['Data Criação'].notna()]
                        df_filtrado_sp = df_filtrado_sp[(df_filtrado_sp['Data Criação'].dt.date >= hist_inicio) & (df_filtrado_sp['Data Criação'].dt.date <= hist_fim)]
            # Caso não esteja em modo histórico, df_filtrado_sp já foi calculado acima a partir das sprints
            
            # === SEÇÃO 2: MÉDIA POR STORY POINTS ===
            st.subheader("Média de Dias por Story Points")
            
            # Calcular médias para story points específicos
            # Considerar SP usuais e incluir 21 quando presente
            # Usar Story Points candidatos da configuração
            sp_candidatos = config.STORY_POINTS_CANDIDATOS
            sp_vals_unique = df_filtrado_sp['Story Points'].dropna().unique()
            sp_presentes = []
            for spv in sp_vals_unique:
                try:
                    sp_int = int(float(spv))
                    if sp_int in sp_candidatos:
                        sp_presentes.append(sp_int)
                except Exception:
                    continue
            sp_presentes = sorted(set(sp_presentes))
            story_points_valores = sp_presentes  # somente exibir se houver
            col_metrics = st.columns(len(story_points_valores) if story_points_valores else 1)
            
            df_resolvidos = df_filtrado_sp[df_filtrado_sp['Dias para Resolução'].notna()]
            
            if story_points_valores:
                for idx, sp_valor in enumerate(story_points_valores):
                    with col_metrics[idx if story_points_valores else 0]:
                        df_sp_especifico = df_resolvidos[df_resolvidos['Story Points'] == sp_valor]
                        media_dias = df_sp_especifico['Dias para Resolução'].mean()
                        total_itens = len(df_sp_especifico)
                        metric(label=f"📈 {sp_valor} SP", value=(f"{media_dias:.1f} dias" if total_itens > 0 else "Sem dados"), delta=f"{total_itens} itens")
            else:
                st.info("Sem Story Points candidatos (3,5,8,13,21) presentes nos dados filtrados.")
            
            # === SEÇÃO 2.1: TABELA DE MÉDIA POR TIPO E STORY POINTS ===
            st.subheader("Média por Tipo e Story Points (Dias para Resolução)")
            if not df_resolvidos.empty:
                # Mapear tipos normalizados para nomes canônicos (utilitário)
                def canonical_type(s_norm: str) -> str:
                    if s_norm == normalize('História'):
                        return 'História'
                    if s_norm == normalize('Débito Técnico'):
                        return 'Débito Técnico'
                    if s_norm == normalize('Spike'):
                        return 'Spike'
                    return s_norm
 
                df_tmp = df_resolvidos.copy()
                # Garantir dtypes numéricos antes de agregar
                df_tmp['Dias para Resolução'] = pd.to_numeric(df_tmp['Dias para Resolução'], errors='coerce')
                df_tmp['Story Points'] = pd.to_numeric(df_tmp['Story Points'], errors='coerce')
                df_tmp = df_tmp.dropna(subset=['Dias para Resolução'])
                df_tmp['TipoNorm'] = df_tmp['Tipo de Item'].apply(normalize).apply(canonical_type)
                agrupado = df_tmp.groupby(['Story Points', 'TipoNorm'])['Dias para Resolução'].mean().reset_index()
                agrupado['Dias para Resolução'] = pd.to_numeric(agrupado['Dias para Resolução'], errors='coerce').round(1)
                # Filtrar apenas SP candidatos presentes
                if story_points_valores:
                    agrupado = agrupado[agrupado['Story Points'].isin(story_points_valores)]
                else:
                    agrupado = agrupado[agrupado['Story Points'].isin(config.STORY_POINTS_CANDIDATOS) & (agrupado['Story Points'].isin(df_resolvidos['Story Points'].unique()))]
                # Pivotar para colunas por tipo
                tabela = agrupado.pivot(index='Story Points', columns='TipoNorm', values='Dias para Resolução').reset_index()
                # Forçar numérico nas colunas de tipo
                for col_num in ['História', 'Débito Técnico', 'Spike']:
                    if col_num in tabela.columns:
                        tabela[col_num] = pd.to_numeric(tabela[col_num], errors='coerce')
                # Ordenar por SP
                tabela = tabela.sort_values('Story Points')
                # Garantir colunas na ordem desejada
                colunas_ordenadas = ['Story Points', 'História', 'Débito Técnico', 'Spike']
                for c in colunas_ordenadas:
                    if c not in tabela.columns:
                        tabela[c] = pd.NA
                tabela = tabela[colunas_ordenadas]

                # Cópia para exibição mantendo NaN como ausente (evita misturar tipos)
                tabela_display = tabela.copy()
                for c in ['História', 'Débito Técnico', 'Spike']:
                    if c in tabela_display.columns:
                        tabela_display[c] = pd.to_numeric(tabela_display[c], errors='coerce').round(1)
                show_df(tabela_display, use_container_width=True, hide_index=True)
            else:
                st.info("Sem dados resolvidos para calcular as médias por tipo.")
            
            # === SEÇÃO 3: GRÁFICOS ===
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                # Gráfico de barras - Média por Story Points
                if not df_resolvidos.empty:
                    media_por_sp = df_resolvidos.groupby('Story Points')['Dias para Resolução'].agg(['mean', 'count']).reset_index()
                    media_por_sp.columns = ['Story Points', 'Média Dias', 'Total Itens']
                    
                    fig_media_sp = bar(media_por_sp, x='Story Points', y='Média Dias', title='Média de Dias por Story Points', color='Média Dias')
                    fig_media_sp.update_traces(text=media_por_sp['Total Itens'], textposition='outside')
                    fig_media_sp.update_traces(textposition='outside')
                    fig_media_sp.update_layout(showlegend=False)
                    st.plotly_chart(fig_media_sp, use_container_width=True)
                else:
                    st.info("📊 Sem dados de resolução para gerar o gráfico")
            
            with col_graf2:
                # Gráfico de dispersão - Story Points vs Dias
                if not df_resolvidos.empty:
                    fig_scatter_sp = scatter(
                        df_resolvidos,
                        x='Story Points',
                        y='Dias para Resolução',
                        color='Tipo de Item',
                        title='Story Points vs Dias para Resolução',
                        hover_data=['Chave', 'Resumo']
                    )
                    st.plotly_chart(fig_scatter_sp, use_container_width=True)
                else:
                    st.info("Sem dados de resolução para gerar o gráfico")
            
            # === SEÇÃO 4: TABELA DETALHADA ===
            st.subheader("Dados Detalhados")
            
            # Preparar dados para exibição
            colunas_exibir = ['Chave', 'Resumo', 'Tipo de Item', 'Story Points', 'Status', 'Responsável', 'Dias para Resolução']
            # Preferir apenas 'Sprint Nome' quando disponível (remover 'Sprint ID')
            if 'Sprint Nome' in df_filtrado_sp.columns and 'Sprint Nome' not in colunas_exibir:
                colunas_exibir.insert(-1, 'Sprint Nome')
            
            df_exibir = df_filtrado_sp[colunas_exibir].copy()
            
            # Configurar colunas da tabela (helper)
            column_config = build_column_config(colunas_exibir)
            
            show_df(
                df_exibir,
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
            
            # === SEÇÃO 5: ESTATÍSTICAS RESUMO ===
            st.subheader("Estatísticas Resumo")
            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
            
            with col_stats1:
                metric("Total de Itens", len(df_filtrado_sp))
            
            with col_stats2:
                itens_resolvidos = len(df_resolvidos)
                metric("Itens Resolvidos", itens_resolvidos)
            
            with col_stats3:
                if not df_resolvidos.empty:
                    media_geral = df_resolvidos['Dias para Resolução'].mean()
                    metric("Média Geral", f"{media_geral:.1f} dias")
                else:
                    metric("Média Geral", "Sem dados")
            
            with col_stats4:
                total_sp = df_filtrado_sp['Story Points'].sum()
                metric("Total Story Points", total_sp)

            # === TABELA AGRUPADA (SP x Média dias resolução) ===
            st.subheader("Story Points x Média (dias) de Resolução")
            if not df_resolvidos.empty:
                df_tbl = df_resolvidos.copy()
                # Status concluído já garantido pela JQL, mas normalizamos SP
                df_tbl['Story Points'] = pd.to_numeric(df_tbl['Story Points'], errors='coerce')
                df_tbl = df_tbl.dropna(subset=['Story Points'])
                df_tbl['SP'] = df_tbl['Story Points'].astype(int)
                df_tbl = df_tbl[df_tbl['SP'].isin(config.STORY_POINTS_CANDIDATOS)]
                if not df_tbl.empty:
                    # Garantir numérico em Dias para Resolução
                    df_tbl['Dias para Resolução'] = pd.to_numeric(df_tbl['Dias para Resolução'], errors='coerce')
                    df_tbl = df_tbl.dropna(subset=['Dias para Resolução'])
                    tabela_media_sp = (
                        df_tbl.groupby('SP')['Dias para Resolução']
                        .mean()
                        .reset_index()
                        .rename(columns={'Dias para Resolução':'Média (dias) Resolução'})
                    )
                    # Arredondar e tipar após garantir float
                    tabela_media_sp['Média (dias) Resolução'] = (
                        tabela_media_sp['Média (dias) Resolução'].astype(float).round(0).astype('Int64')
                    )
                    tabela_media_sp = tabela_media_sp.sort_values('SP')
                    show_df(tabela_media_sp, use_container_width=True, hide_index=True)
                else:
                    st.info(f"Sem SP válidos {config.STORY_POINTS_CANDIDATOS} no período.")
            else:
                st.info("Sem itens resolvidos no período para calcular as médias.")

# Fim do bloco principal do dashboard

else:
    st.info("Carregue os dados da sprint para visualizar as métricas e análises.")
    st.markdown("""
    ### Como começar:
    1. **Configure a API:** Use a sidebar para inserir URL, email e token
    2. **Selecione o projeto:** Escolha o projeto Jira
    3. **Escolha a(s) sprint(s):** Selecione uma ou múltiplas sprints
    4. **Clique em "Carregar Dados"** para gerar o dashboard
    """)

# Footer
st.markdown("---")
st.markdown(
    "**Dashboard desenvolvido para análise de sprints Jira** | "
    "Baseado em Streamlit e Plotly | "
    f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)