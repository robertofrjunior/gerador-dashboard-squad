#!/usr/bin/env python3
"""
Interface Web para Dashboard de Análise de Sprint Jira
Desenvolvido com Streamlit para facilitar a visualização das métricas.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Importar módulos do projeto
from credcesta import sprint_service, charts, settings
from jiraproject.utils_constants import TIPOS_AGEIS_CANON, STATUS_CONCLUIDO, STORY_POINTS_PADRAO
from jiraproject.utils_normalize import normalize, canonical_type
from jiraproject.utils_arrow import to_arrow_safe_numeric, make_display_copy
from jiraproject.utils_dates import compute_days_resolution
from jiraproject.services import jira as jira_service
from jiraproject.utils.log import info, ok, warn, error
from jiraproject.utils.ui import tipo_icon, status_color, build_column_config, metric, pct_delta, pie, bar

# Helpers internos para reduzir duplicação
def calc_dias(df: pd.DataFrame, created_col: str = 'Data Criação', resolved_col: str = 'Data Resolução', out_col: str = 'Dias para Resolução') -> pd.DataFrame:
    return compute_days_resolution(df, created_col, resolved_col, out_col=out_col)


def show_df(df: pd.DataFrame, **kwargs):
    st.dataframe(make_display_copy(df), **kwargs)
@st.cache_data(show_spinner="Buscando sprints do projeto...", ttl=300)  # Cache por 5 minutos
def buscar_sprints_do_projeto_cache(_projeto_validado):
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
def resolver_nome_projeto(_projeto_input):
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
    elif 'credcesta' in input_lower:
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
def validar_sprints_especificas(_projeto, _sprint_ids):
    """
    Valida apenas os IDs de sprint especificados pelo usuário.
    NÃO faz busca exaustiva.
    
    Args:
        _projeto (str): Nome do projeto
        _sprint_ids (list): Lista de IDs de sprint para validar
        
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

@st.cache_data(show_spinner="Carregando projetos do Jira...", ttl=600)
def listar_projetos_cache():
    """Retorna a lista de projetos do Jira (key e name)."""
    try:
        return jira_service.listar_projetos()
    except Exception as e:
        error(f"Erro ao carregar projetos: {e}")
        return []

# Função para criar URLs do Jira (removida - não está mais sendo usada)
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

# Título principal
if 'df' in st.session_state and not st.session_state['df'].empty:
    # Título dinâmico com informações da sprint
    projeto = st.session_state.get('projeto', 'N/A')
    sprint_nome = st.session_state['df'].attrs.get('sprint_nome', f"Sprint {st.session_state.get('sprint_id', 'N/A')}")
    sprint_inicio = st.session_state['df'].attrs.get('sprint_inicio')
    sprint_fim = st.session_state['df'].attrs.get('sprint_fim')

    # Formatar datas se disponíveis
    periodo_texto = ""
    if sprint_inicio and sprint_fim:
        try:
            from datetime import datetime
            inicio_dt = datetime.fromisoformat(sprint_inicio.replace('Z', '+00:00'))
            fim_dt = datetime.fromisoformat(sprint_fim.replace('Z', '+00:00'))
            periodo_texto = f" ({inicio_dt.strftime('%d/%m/%Y')} - {fim_dt.strftime('%d/%m/%Y')})"
        except:
            periodo_texto = ""

    titulo_dinamico = f"🎯 {projeto} - {sprint_nome}{periodo_texto}"
    st.markdown(f'<h1 class="main-header">{titulo_dinamico}</h1>', unsafe_allow_html=True)
else:
    st.markdown('<h1 class="main-header">🎯 Dashboard de Análise de Sprint Jira</h1>', unsafe_allow_html=True)

# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações da Análise")
    
    # Seção de entrada de dados
    st.subheader("📋 Dados da Sprint")
    
    # Lista de projetos comuns para ajudar o usuário
    projetos_sugeridos = [
        "SMD",
        "[DIGITAL] Sites / Marketing", 
        "[DIGITAL] CredCesta CORE",
        "VAC",
        "smd",
        "vac"
    ]
    
    # Input para projeto com selectbox opcional
    col_projeto1, col_projeto2 = st.columns([3, 1])
    
    with col_projeto1:
        projeto_input = st.text_input(
            "Nome do Projeto/Squad",
            value=st.session_state.get('projeto', ''),
            help="Digite o nome exato do projeto no Jira",
            placeholder="Ex: SMD, [DIGITAL] Sites / Marketing, CredCesta...",
            key="projeto_input"
        )
    
    with col_projeto2:
        # Listar squads (boards) priorizando nomes com [SPRINT]
        squads = jira_service.listar_squads()
        squad_selecionada = st.selectbox(
            "Squads (Boards)",
            options=squads if squads else [],
            format_func=lambda s: f"{s['key']} — {s['board_name']} ({s['name']})" if isinstance(s, dict) else str(s),
            key="squad_select"
        )
        if squad_selecionada:
            st.session_state['projeto_key'] = squad_selecionada['key']  # ex.: VAC
            st.session_state['projeto_name'] = squad_selecionada['name']
            st.session_state['board_id'] = squad_selecionada['board_id']
            projeto_input = squad_selecionada['key']

    # Atualiza o session_state apenas se o input mudou E não está vazio
    if projeto_input and projeto_input != st.session_state.get('projeto'):
        st.session_state['projeto'] = projeto_input
        # Limpar dados relacionados ao projeto anterior
        keys_to_clear = ['sprints_selecionadas', 'sprints_validadas', 'df', 'sprint_info', 'selectbox_sprint', 'sprint_ids_input']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        # Usar flag para limpar campo de sprint na próxima execução
        st.session_state['clear_sprint_input'] = True
        # Limpar todos os caches para forçar rebusca
        st.cache_data.clear()
        st.rerun()
        
    # NOVA LÓGICA SIMPLIFICADA: Validar projeto e aguardar input de sprints
    projeto_validado = None
    # Se veio do select de squads (boards), já está validado (usar key)
    if st.session_state.get('projeto_key'):
        projeto_validado = st.session_state['projeto_key']
        st.success(f"✅ Squad/Projeto validado: {st.session_state['projeto_key']} — {st.session_state.get('projeto_name', '')}")
    elif projeto_input and len(projeto_input.strip()) > 0:
        # Fallback: validar input manual
        try:
            projeto_correto, é_válido, mensagem_validacao = resolver_nome_projeto(projeto_input)
            if é_válido:
                projeto_validado = projeto_correto
                st.success(f"✅ Projeto validado: {mensagem_validacao}")
            else:
                st.error(f"❌ {mensagem_validacao}")
                st.markdown("""
                **💡 Verifique o nome do projeto:**
                - Use a sigla do projeto (ex.: VAC, SMD)
                - Ou selecione diretamente na lista de Squads (boards)
                """)
        except Exception as e:
            st.error(f"❌ Erro na validação do projeto: {e}")

    # NOVA INTERFACE: Mostrar Sprint Atual e Recentes
    st.subheader("📋 Selecione as Sprints")
    
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
                    st.success(f"🎯 **Sprint Atual:** {sprint_atual['nome']} (ID: {sprint_atual['id']}) - Estado: {sprint_atual.get('estado', 'Desconhecido')}")
                    
                    # Adicionar sprint atual
                    opcoes_sprint.append({
                        'id': sprint_atual['id'],
                        'nome': sprint_atual['nome'],
                        'label': f"🎯 {sprint_atual['nome']} (ID: {sprint_atual['id']}) - ATUAL",
                        'is_current': True
                    })
                
                # Adicionar 5 sprints anteriores
                if sprints_do_board.get('recentes'):
                    for sprint in sprints_do_board['recentes'][:5]:  # Apenas 5 anteriores
                        opcoes_sprint.append({
                            'id': sprint['id'],
                            'nome': sprint['nome'],
                            'label': f"📅 {sprint['nome']} (ID: {sprint['id']})",
                            'is_current': False
                        })
                
                # Adicionar opção para múltiplas sprints
                if len(opcoes_sprint) > 1:
                    opcoes_sprint.append({
                        'id': 'multiple',
                        'nome': 'Múltiplas Sprints',
                        'label': f"📊 Analisar Todas ({len(opcoes_sprint)} sprints)",
                        'is_current': False,
                        'is_multiple': True
                    })
                
                if opcoes_sprint:
                    st.divider()
                    st.subheader("🏃‍♀️ Selecionar Sprint")
                    
                    # Criar lista de labels para o selectbox
                    labels_opcoes = [opcao['label'] for opcao in opcoes_sprint]
                    
                    # Selectbox para escolher sprint
                    sprint_escolhida = st.selectbox(
                        "Escolha uma sprint para analisar:",
                        options=labels_opcoes,
                        index=0,  # Sprint atual como padrão
                        key="selectbox_sprint"
                    )
                    
                    # Encontrar a sprint selecionada
                    if sprint_escolhida:
                        sprint_selecionada = None
                        for opcao in opcoes_sprint:
                            if opcao['label'] == sprint_escolhida:
                                sprint_selecionada = opcao
                            break
                        
                        if sprint_selecionada:
                            # Mostrar detalhes da sprint selecionada
                            col_info, col_botao = st.columns([2, 1])
                            
                            with col_info:
                                if sprint_selecionada.get('is_multiple'):
                                    # Opção de múltiplas sprints
                                    st.info(f"📊 **Selecionada:** Análise de Múltiplas Sprints ({len(opcoes_sprint)-1} sprints)")
                                    st.caption("Inclui a sprint atual e as 5 anteriores")
                                elif sprint_selecionada['is_current']:
                                    st.info(f"🎯 **Selecionada:** Sprint Atual - {sprint_selecionada['nome']}")
                                else:
                                    st.info(f"📅 **Selecionada:** {sprint_selecionada['nome']} (Sprint Anterior)")
                            
                            with col_botao:
                                if st.button("📊 Analisar Sprint Selecionada", type="primary", use_container_width=True, key="btn_analisar_selecionada"):
                                    if sprint_selecionada.get('is_multiple'):
                                        # Coletar IDs de todas as sprints (exceto a opção múltipla)
                                        todos_ids = []
                                        for opcao in opcoes_sprint:
                                            if not opcao.get('is_multiple') and opcao['id'] != 'multiple':
                                                todos_ids.append(str(opcao['id']))
                                        st.session_state['selected_sprint_ids'] = ', '.join(todos_ids)
                                    else:
                                        st.session_state['selected_sprint_ids'] = str(sprint_selecionada['id'])
                                    st.rerun()
                
                st.divider()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível buscar sprints automaticamente: {str(e)[:100]}")
    
    # Campo manual para entrada de sprints
    col_manual, col_acoes = st.columns([3, 1])
    
    with col_manual:
        # Determinar valor inicial baseado nos flags
        if st.session_state.get('clear_sprint_input', False):
            valor_input = ''
            del st.session_state['clear_sprint_input']
        else:
            valor_input = st.session_state.get('selected_sprint_ids', st.session_state.get('sprint_ids_input', ''))
        
        # Input de texto para múltiplas sprints
        sprint_ids_text = st.text_input(
            "Ou digite IDs manualmente (separados por vírgula)",
            value=valor_input,
            placeholder="Ex: 2614, 2615, 2616",
            help="Digite um ou mais IDs de sprint separados por vírgula",
            key='sprint_ids_input',
            disabled=not projeto_validado
        )
        
        # Limpar o valor selecionado após usar
        if 'selected_sprint_ids' in st.session_state:
            del st.session_state['selected_sprint_ids']
    
    with col_acoes:
        st.write("") # Espaço
        st.write("") # Espaço
        if st.button("🔄 Limpar", use_container_width=True, disabled=not projeto_validado):
            # Usar um flag para limpar na próxima execução
            st.session_state['clear_sprint_input'] = True
            if 'sprints_validadas' in st.session_state:
                del st.session_state['sprints_validadas']
            st.rerun()
    
    # Converter texto em lista de IDs
    sprints_selecionadas = []
    if sprint_ids_text:
        try:
            # Parse dos IDs
            ids_raw = sprint_ids_text.replace(' ', '').split(',')
            sprints_selecionadas = [int(id_str) for id_str in ids_raw if id_str.isdigit()]
            
            if sprints_selecionadas:
                # Mostrar resumo das sprints selecionadas
                st.info(f"📌 **{len(sprints_selecionadas)} sprint(s) selecionada(s):** {', '.join(map(str, sprints_selecionadas))}")
                
                # Se tiver sprints do board, mostrar nomes
                if sprints_do_board:
                    nomes_sprints = []
                    todas_sprints = []
                    
                    if sprints_do_board.get('ativa'):
                        todas_sprints.append(sprints_do_board['ativa'])
                    todas_sprints.extend(sprints_do_board.get('recentes', []))
                    
                    for sprint_id in sprints_selecionadas:
                        for sprint in todas_sprints:
                            if sprint['id'] == sprint_id:
                                nomes_sprints.append(f"{sprint['nome']} ({sprint_id})")
                                break
                        else:
                            nomes_sprints.append(f"Sprint {sprint_id}")
                    
                    if nomes_sprints:
                        st.write("**Sprints:** " + " | ".join(nomes_sprints))
                
        except ValueError as e:
            st.error(f"❌ Formato inválido. Use números separados por vírgula")
    
    # Validação e botão para buscar dados
    st.divider()
    projeto_final = projeto_validado if projeto_validado else projeto_input
    
    # Validar sprints antes de permitir busca
    if not projeto_final or len(projeto_final.strip()) == 0:
        st.warning("⚠️ Digite o nome do projeto para continuar")
    elif not projeto_validado and projeto_input:
        st.warning("⚠️ Projeto precisa ser validado antes de buscar dados")
    elif not sprints_selecionadas:
        st.warning("⚠️ Digite os IDs das sprints que deseja analisar")
    else:
        # Validar as sprints selecionadas
        col_validacao, col_botao = st.columns([2, 1])
        
        with col_validacao:
            if st.button("✔️ Validar Sprints", use_container_width=True):
                with st.spinner("Validando sprints..."):
                    validas, invalidas = validar_sprints_especificas(projeto_final, sprints_selecionadas)
                    
                    if validas:
                        st.session_state['sprints_validadas'] = validas
                        st.success(f"✅ {len(validas)} sprint(s) válida(s)")
                    if invalidas:
                        st.warning(f"⚠️ {len(invalidas)} sprint(s) inválida(s): {invalidas}")
        
        with col_botao:
            # Só ativar se tiver sprints validadas
            sprints_validadas = st.session_state.get('sprints_validadas', [])
            botao_ativo = bool(projeto_validado and sprints_validadas)
            
            if st.button(
                "🔍 Buscar Dados", 
                type="primary", 
                use_container_width=True, 
                disabled=not botao_ativo,
                help="Valide as sprints primeiro" if not sprints_validadas else "Buscar dados das sprints validadas"
            ):
                if projeto_final and sprints_validadas:
                    with st.spinner("🔄 Buscando dados do Jira..."):
                        try:
                            # Buscar dados apenas das sprints validadas
                            dfs_sprints = []
                            sprints_com_erro = []
                            sprints_sem_dados = []
                            sprint_info = []
                            
                            for sprint_id in sprints_validadas:
                                try:
                                    df_sprint = sprint_service.analisar_sprint(projeto_final, sprint_id)
                                    if not df_sprint.empty:
                                        # Adicionar coluna identificando a sprint
                                        df_sprint['Sprint ID'] = sprint_id
                                        df_sprint['Sprint Nome'] = df_sprint.attrs.get('sprint_nome', f'Sprint {sprint_id}')
                                        dfs_sprints.append(df_sprint)
                                        
                                        # Coletar informações da sprint
                                        sprint_info.append({
                                            'id': sprint_id,
                                            'nome': df_sprint.attrs.get('sprint_nome', f'Sprint {sprint_id}'),
                                            'inicio': df_sprint.attrs.get('sprint_inicio'),
                                            'fim': df_sprint.attrs.get('sprint_fim'),
                                            'total_itens': len(df_sprint)
                                        })
                                    else:
                                        sprints_sem_dados.append(sprint_id)
                                except Exception as e:
                                    error_msg = str(e)
                                    if "404" in error_msg:
                                        sprints_com_erro.append(f"Sprint {sprint_id} (não encontrada)")
                                    elif "400" in error_msg:
                                        sprints_com_erro.append(f"Sprint {sprint_id} (projeto inválido)")
                                    else:
                                        sprints_com_erro.append(f"Sprint {sprint_id} (erro: {str(e)[:30]}...)")
                            
                            # Mostrar avisos detalhados para sprints com problemas
                            if sprints_com_erro or sprints_sem_dados:
                                problemas = []
                                if sprints_com_erro:
                                    problemas.extend(sprints_com_erro)
                                if sprints_sem_dados:
                                    for sprint_id in sprints_sem_dados:
                                        problemas.append(f"Sprint {sprint_id} (sem issues)")
                                
                                st.warning(f"⚠️ Problemas encontrados: {', '.join(problemas)}")
                                
                                # Sugestões de soluções
                                if sprints_com_erro:
                                    st.markdown("""
                                    **💡 Possíveis soluções:**
                                    - **404 (não encontrada):** Verifique se o ID da sprint existe
                                    - **400 (projeto inválido):** Confirme se o nome do projeto está correto
                                    - **Sem issues:** A sprint pode estar vazia ou ter problemas de permissão
                                    """)
                            
                            if dfs_sprints:
                                # Combinar todos os DataFrames
                                df_combinado = pd.concat(dfs_sprints, ignore_index=True)
                                
                                # Armazenar no session_state
                                st.session_state['df'] = df_combinado
                                st.session_state['projeto'] = projeto_final
                                st.session_state['sprints_selecionadas'] = sprints_validadas
                                st.session_state['sprint_info'] = sprint_info
                                st.session_state['total_sprint'] = len(df_combinado)
                                
                                # Para compatibilidade com código existente
                                st.session_state['sprint_id'] = sprints_validadas[0] if len(sprints_validadas) == 1 else "Múltiplas"
                                st.session_state['sprint_nome'] = sprint_info[0]['nome'] if len(sprint_info) == 1 else f"{len(sprints_validadas)} Sprints"
                                st.session_state['sprint_inicio'] = sprint_info[0]['inicio'] if len(sprint_info) == 1 else None
                                st.session_state['sprint_fim'] = sprint_info[0]['fim'] if len(sprint_info) == 1 else None
                                
                                st.success(f"✅ Dados de {len(dfs_sprints)} sprint(s) carregados com sucesso! ({len(df_combinado)} issues no total)")
                                st.rerun()
                            else:
                                st.error("❌ Nenhum dado válido encontrado para as sprints selecionadas")
                                st.markdown("""
                                **💡 O que verificar:**
                                1. **Nome do projeto:** Confirme se está exatamente como aparece no Jira
                                2. **IDs das sprints:** Verifique se os números estão corretos
                                3. **Permissões:** Certifique-se de que tem acesso ao projeto e sprints
                                4. **Configuração da API:** Verifique URL, email e token nas configurações
                                """)
                        except Exception as e:
                            st.error(f"❌ Erro ao buscar dados: {str(e)}")
    
    # Informações da última busca
    if 'df' in st.session_state:
        st.divider()
        st.subheader("📋 Última Análise")
        
        # Mostrar informações das sprints
        if 'sprint_info' in st.session_state and st.session_state['sprint_info']:
            sprint_info = st.session_state['sprint_info']
            if len(sprint_info) == 1:
                # Uma única sprint
                info = sprint_info[0]
                st.info(f"""
                **Projeto:** {st.session_state.get('projeto', 'N/A')}  
                **Sprint:** {info['nome']} (ID: {info['id']})  
                **Total de Issues:** {info['total_itens']}
                """)
            else:
                # Múltiplas sprints
                total_issues = sum(info['total_itens'] for info in sprint_info)
                sprint_ids = [str(info['id']) for info in sprint_info]
                
                st.info(f"""
                **Projeto:** {st.session_state.get('projeto', 'N/A')}  
                **Sprints:** {len(sprint_info)} sprints ({', '.join(sprint_ids)})  
                **Total de Issues:** {total_issues}
                """)
                
                # Mostrar detalhes de cada sprint em uma tabela compacta
                st.subheader("📊 Detalhes por Sprint")
                sprint_details = []
                for info in sprint_info:
                    sprint_details.append({
                        'Sprint ID': info['id'],
                        'Nome': info['nome'],
                        'Total Issues': info['total_itens']
                    })
                
                import pandas as pd
                df_sprint_details = pd.DataFrame(sprint_details)
                show_df(df_sprint_details, use_container_width=True, hide_index=True)
        else:
            # Fallback para compatibilidade
            st.info(f"""
            **Projeto:** {st.session_state.get('projeto', 'N/A')}  
            **Sprint:** {st.session_state.get('sprint_id', 'N/A')}  
            **Total de Issues:** {st.session_state.get('total_sprint', 0)}
            """)
            
            if st.button("🗑️ Limpar Dados", use_container_width=True):
                keys_to_clear = ['df', 'projeto', 'sprint_id', 'total_sprint', 'sprint_nome', 
                               'sprint_inicio', 'sprint_fim', 'sprints_selecionadas', 'sprint_info']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

# Conteúdo principal
if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    projeto = st.session_state.get('projeto', 'N/A')
    sprint_id = st.session_state.get('sprint_id', 'N/A')
    total_sprint = st.session_state.get('total_sprint', len(df))
    
    # Métricas principais
    st.subheader("📈 Métricas Principais da Sprint")
    
    tipos_ageis = TIPOS_AGEIS_CANON
    df_ageis = df[df['Tipo de Item'].apply(lambda x: canonical_type(normalize(x)) in tipos_ageis)]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        metric("🎫 Total de Issues", total_sprint, help_text="Total de issues na sprint (todos os tipos)")
    
    with col2:
        total_ageis = len(df_ageis)
        pct_ageis = (total_ageis / total_sprint * 100) if total_sprint > 0 else 0
        metric("📗 Itens Ágeis", total_ageis, delta=pct_delta(total_ageis, total_sprint), help_text="História, Débito Técnico e Spike")
    
    with col3:
        total_sp = df_ageis['Story Points'].sum()
        metric("⭐ Story Points", f"{total_sp:.0f}", help_text="Total de story points planejados")
    
    with col4:
        concluidos = len(df[df['Status'].isin(STATUS_CONCLUIDO)])
        pct_concluidos = (concluidos / total_sprint * 100) if total_sprint > 0 else 0
        metric("✅ Concluídos", concluidos, delta=pct_delta(concluidos, total_sprint), help_text="Items com status de conclusão")
    

    
    # Tabs para diferentes visualizações
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Visão Geral",
        "👥 Análise por Responsável",
        "📋 Dados Detalhados",
        "⏱️ Tempo de Conclusão",
        "🐛 Bugs & Impedimentos",
        "📈 Story Points"
    ])
    
    with tab1:
        st.subheader("🎯 Visão Executiva da Sprint")
        
        # === SEÇÃO 1: CONTADOR SUMARIZADO ===
        st.subheader("📊 Resumo Executivo")
        
        # Filtrar apenas itens ágeis (História, Débito Técnico, Spike, Bug)
        tipos_ageis_exec = TIPOS_AGEIS_CANON + ['Bug']
        df_exec = df[df['Tipo de Item'].apply(lambda x: canonical_type(normalize(x)) in tipos_ageis_exec)]
        
        # Contadores por tipo
        contador_tipos = df_exec['Tipo de Item'].value_counts()
        total_itens_exec = len(df_exec)
        
        # Métricas em cards
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            metric("🎫 Total Itens", total_itens_exec, help_text="Total de itens ágeis na sprint")
        
        with col2:
            historias = contador_tipos.get('História', 0)
            pct_hist = (historias / total_itens_exec * 100) if total_itens_exec > 0 else 0
            metric("📗 Histórias", historias, delta=pct_delta(historias, total_itens_exec), help_text="Histórias de usuário")
        
        with col3:
            debitos = contador_tipos.get('Débito Técnico', 0) + contador_tipos.get('Debito Tecnico', 0)
            pct_debt = (debitos / total_itens_exec * 100) if total_itens_exec > 0 else 0
            metric("🔧 Débitos", debitos, delta=pct_delta(debitos, total_itens_exec), help_text="Débitos técnicos")
        
        with col4:
            spikes = contador_tipos.get('Spike', 0)
            pct_spike = (spikes / total_itens_exec * 100) if total_itens_exec > 0 else 0
            metric("⚡ Spikes", spikes, delta=pct_delta(spikes, total_itens_exec), help_text="Investigações e spikes")
        
        with col5:
            bugs = contador_tipos.get('Bug', 0)
            pct_bug = (bugs / total_itens_exec * 100) if total_itens_exec > 0 else 0
            metric("🐛 Bugs", bugs, delta=pct_delta(bugs, total_itens_exec), help_text="Correções de bugs")
        
        st.markdown("---")
        
        # === SEÇÃO 2: LISTA DETALHADA DOS ITENS ===
        st.subheader("🎫 Itens da Sprint - Visão Detalhada")
        
        if not df_exec.empty:
            # Preparar dados para exibição
            df_exec_display = df_exec[['Chave', 'Tipo de Item', 'Resumo', 'Status']].copy()
            
            # Adicionar coluna de ícone baseada no tipo
            df_exec_display['Tipo'] = df_exec_display['Tipo de Item'].apply(lambda x: f"{tipo_icon(x)} {x}")
            
            # Reorganizar colunas (voltar ao formato original)
            df_exec_display = df_exec_display[['Chave', 'Tipo', 'Resumo', 'Status']]
            
            # Configurar exibição da tabela
            st.dataframe(
                make_display_copy(df_exec_display),
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config=build_column_config(['Chave', 'Tipo', 'Resumo', 'Status'])
            )
            
            # Estatísticas adicionais
            st.subheader("📈 Estatísticas por Status")
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
                # Tabela resumo por tipo
                st.subheader("Resumo por Tipo")
                resumo_tipos_exec = df_exec.groupby('Tipo de Item').agg({
                    'Chave': 'count'
                }).rename(columns={'Chave': 'Quantidade'}).reset_index()
                
                resumo_tipos_exec['Percentual'] = (resumo_tipos_exec['Quantidade'] / total_itens_exec * 100).round(1)
                resumo_tipos_exec['Percentual'] = resumo_tipos_exec['Percentual'].astype(str) + '%'
                
                # Adicionar ícones
                resumo_tipos_exec['Tipo'] = resumo_tipos_exec['Tipo de Item'].apply(lambda x: f"{tipo_icon(x)} {x}")
                resumo_tipos_exec = resumo_tipos_exec[['Tipo', 'Quantidade', 'Percentual']]
            
            show_df(resumo_tipos_exec, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Nenhum item ágil encontrado na sprint.")

    
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
            resumo_responsaveis['Pct_Itens'] = (resumo_responsaveis['Total_Itens'] / len(df) * 100).round(1)
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

                    fig_tipo_resp = pie(values=tipo_resp_counts.values, names=tipo_resp_counts.index, title=f'Tipos de Item - {responsavel_selecionado}', color_sequence=px.colors.qualitative.Set2)
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
    
    with tab3:
        st.subheader("📋 Dados Detalhados da Sprint")
        
        # Filtros
        st.subheader("🔍 Filtros")
        col_filtro1, col_filtro2 = st.columns(2)
        
        with col_filtro1:
            # Filtro por Tipo de Item
            tipos_disponiveis = ['Todos'] + sorted(df['Tipo de Item'].unique().tolist())
            tipos_selecionados = st.multiselect(
                "Filtrar por Tipo de Item",
                options=tipos_disponiveis,
                default=['Todos'],
                help="Selecione os tipos de item para filtrar"
            )
        
        with col_filtro2:
            # Filtro por Sprint (se múltiplas sprints estão carregadas)
            if 'Sprint ID' in df.columns:
                sprints_disponiveis = ['Todas'] + sorted(df['Sprint ID'].unique().tolist())
                sprints_filtro = st.multiselect(
                    "Filtrar por Sprint",
                    options=sprints_disponiveis,
                    default=['Todas'],
                    help="Selecione as sprints para filtrar"
                )
            else:
                sprints_filtro = ['Todas']
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        # Filtro por tipo
        if tipos_selecionados and 'Todos' not in tipos_selecionados:
            df_filtrado = df_filtrado[df_filtrado['Tipo de Item'].isin(tipos_selecionados)]
        
        # Filtro por sprint
        if 'Sprint ID' in df_filtrado.columns and sprints_filtro and 'Todas' not in sprints_filtro:
            df_filtrado = df_filtrado[df_filtrado['Sprint ID'].isin(sprints_filtro)]
        
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
        
        # Mostrar estatísticas do filtro
        st.info(f"📊 Exibindo {len(df_filtrado)} de {len(df)} items ({len(df_filtrado)/len(df)*100:.1f}%)")
        
        # Controles de exibição
        st.subheader("⚙️ Configurações de Exibição")
        col1, col2, col3 = st.columns(3)

        with col1:
            colunas_disponiveis = df_filtrado.columns.tolist()
            
            # Definir colunas padrão (principais)
            colunas_principais = ['Chave', 'Resumo', 'Tipo de Item', 'Status', 'Responsável', 'Dias para Resolução']
            
            # Adicionar colunas de Sprint se múltiplas sprints estão carregadas
            if 'Sprint ID' in colunas_disponiveis:
                colunas_principais.insert(-1, 'Sprint ID')  # Antes de 'Dias para Resolução'
            if 'Sprint Nome' in colunas_disponiveis:
                colunas_principais.insert(-1, 'Sprint Nome')  # Antes de 'Dias para Resolução'
            
            colunas_padrao = [col for col in colunas_principais if col in colunas_disponiveis]
            
            colunas_selecionadas = st.multiselect(
                "Selecione as colunas para exibir",
                options=colunas_disponiveis,
                default=colunas_padrao,
                help="Escolha quais colunas mostrar na tabela"
            )

        with col2:
            ordenar_por = st.selectbox(
                "Ordenar por",
                options=df_filtrado.columns.tolist(),
                index=0,
                help="Escolha a coluna para ordenação"
            )
        
        with col3:
            ordem_desc = st.checkbox("Ordem decrescente", value=False)
        
        # Aplicar configurações
        if colunas_selecionadas:
            df_exibir = df_filtrado[colunas_selecionadas].sort_values(
                by=ordenar_por, 
                ascending=not ordem_desc
            )
            
            # Exibir dataframe
            show_df(df_exibir, use_container_width=True, hide_index=True, height=600)
            
            # Estatísticas da tabela
            st.subheader("📈 Estatísticas dos Dados")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                metric("Total de Registros", len(df_exibir))
            
            with col2:
                if 'Tipo de Item' in df_exibir.columns:
                    tipos_unicos_exibir = df_exibir['Tipo de Item'].nunique()
                    metric("Tipos Únicos", tipos_unicos_exibir)
            
            with col3:
                if 'Responsável' in df_exibir.columns:
                    resp_unicos_exibir = df_exibir['Responsável'].nunique()
                    metric("Responsáveis Únicos", resp_unicos_exibir)
            
            with col4:
                if 'Status' in df_exibir.columns:
                    status_unicos_exibir = df_exibir['Status'].nunique()
                    metric("Status Únicos", status_unicos_exibir)
            
            # Segunda linha de métricas - Estatísticas de Tempo
            if 'Dias para Resolução' in df_exibir.columns:
                st.subheader("⏱️ Estatísticas de Tempo")
                col1, col2, col3, col4 = st.columns(4)
                
                # Filtrar apenas itens com dias calculados (não nulos)
                dias_validos = df_exibir['Dias para Resolução'].dropna()
                
                with col1:
                    if not dias_validos.empty:
                        media_dias = dias_validos.mean()
                        metric("Média de Dias", f"{media_dias:.1f}")
                    else:
                        metric("Média de Dias", "N/A")
                
                with col2:
                    if not dias_validos.empty:
                        mediana_dias = dias_validos.median()
                        metric("Mediana de Dias", f"{mediana_dias:.1f}")
                    else:
                        metric("Mediana de Dias", "N/A")
                
                with col3:
                    if not dias_validos.empty:
                        min_dias = dias_validos.min()
                        metric("Mínimo de Dias", f"{min_dias:.0f}")
                    else:
                        metric("Mínimo de Dias", "N/A")
                
                with col4:
                    if not dias_validos.empty:
                        max_dias = dias_validos.max()
                        metric("Máximo de Dias", f"{max_dias:.0f}")
                    else:
                        metric("Máximo de Dias", "N/A")
            
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
    
    with tab4:
        st.subheader("⏱️ Análise de Tempo de Conclusão")
        
        # Verificar se as colunas de data existem
        if 'Data Criação' not in df.columns or 'Data Resolução' not in df.columns:
            st.warning("⚠️ Dados de tempo não disponíveis. As colunas 'Data Criação' e 'Data Resolução' não foram encontradas.")
            st.info("💡 Esta funcionalidade requer que os dados sejam coletados novamente com as informações de data.")
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
                    metric("🎫 Total de Itens", len(df_tempo), help_text="Itens com datas de criação e resolução válidas")
                
                with col2:
                    media_dias = df_tempo['Dias para Conclusão'].mean()
                    metric("📅 Média de Dias", f"{media_dias:.1f}", help_text="Tempo médio para conclusão")
                
                with col3:
                    min_dias = df_tempo['Dias para Conclusão'].min()
                    metric("🚀 Mínimo", f"{min_dias} dias", help_text="Menor tempo de conclusão")
                
                with col4:
                    max_dias = df_tempo['Dias para Conclusão'].max()
                    metric("🐌 Máximo", f"{max_dias} dias", help_text="Maior tempo de conclusão")
                
                # Análise por tipo de item
                st.subheader("⏱️ Tempo Médio por Tipo de Item")
                tipos_ageis = TIPOS_AGEIS_CANON + ['Bug']
                df_tipos = df_tempo[df_tempo['Tipo de Item'].apply(lambda x: canonical_type(normalize(x)) in tipos_ageis)]
                
                if not df_tipos.empty:
                    medias_por_tipo = df_tipos.groupby('Tipo de Item')['Dias para Conclusão'].agg(['mean', 'count']).reset_index()
                    medias_por_tipo.columns = ['Tipo de Item', 'Média de Dias', 'Quantidade']
                    medias_por_tipo['Média de Dias'] = medias_por_tipo['Média de Dias'].round(1)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Gráfico de barras com médias por tipo
                        fig_medias = bar(
                            medias_por_tipo,
                            x='Tipo de Item',
                            y='Média de Dias',
                            title='Dias Médios para Conclusão por Tipo',
                            color='Tipo de Item',
                            color_map={
                                'História': '#0052cc',
                                'Debito Tecnico': '#ff8b00',
                                'Bug': '#de350b',
                                'Spike': '#00875a'
                            }
                        )
                        fig_medias.update_layout(showlegend=False)
                        st.plotly_chart(fig_medias, use_container_width=True)
                    
                    with col2:
                        # Tabela com estatísticas
                        show_df(
                            medias_por_tipo,
                            use_container_width=True,
                            hide_index=True
                        )
                

                
                # Scatter plot: Story Points vs Dias
                st.subheader("📈 Relação entre Story Points e Tempo de Conclusão")
                fig_scatter = px.scatter(
                    df_tempo,
                    x='Story Points',
                    y='Dias para Conclusão',
                    color='Tipo de Item',
                    size='Story Points',
                    hover_data=['Chave', 'Resumo', 'Responsável'],
                    title='Relação entre Story Points e Tempo de Conclusão',
                    color_discrete_map={
                        'História': '#0052cc',      # Azul Jira - Story
                        'Debito Tecnico': '#ff8b00',  # Laranja Jira - Technical Debt
                        'Bug': '#de350b',            # Vermelho Jira - Bug
                        'Spike': '#00875a'           # Verde Jira - Spike
                    }
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Tabela detalhada
                st.subheader("🎫 Dados Detalhados")
                df_exibir_tempo = df_tempo[['Chave', 'Tipo de Item', 'Resumo', 'Responsável', 'Story Points', 'Dias para Conclusão']].sort_values('Dias para Conclusão', ascending=False)
                
                show_df(df_exibir_tempo, use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("🐛 Bugs & Impedimentos")
        
        # Filtrar itens que são bugs ou impedimentos
        # Bugs: itens do tipo "Bug"
        # Impedimentos: itens com status que contenha palavras relacionadas a impedimento
        
        # Identificar impedimentos por status
        def is_impedimento(status):
            status_lower = status.lower() if pd.notna(status) else ""
            impedimento_keywords = ['impedimento', 'bloqueado', 'blocked', 'impedido', 'pausado', 'paused']
            return any(keyword in status_lower for keyword in impedimento_keywords)
        
        # Filtrar bugs
        df_bugs = df[df['Tipo de Item'].str.contains('Bug', case=False, na=False)]
        
        # Filtrar impedimentos (por status)
        df_impedimentos_status = df[df['Status'].apply(is_impedimento)]
        
        # Combinar bugs e impedimentos, removendo duplicatas
        df_bugs_impedimentos = pd.concat([df_bugs, df_impedimentos_status]).drop_duplicates()
        
        if not df_bugs_impedimentos.empty:
            # Métricas principais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                metric("🐛 Total de Bugs", len(df_bugs), help_text="Itens classificados como Bug")
            
            with col2:
                metric("⚠️ Impedimentos", len(df_impedimentos_status), help_text="Itens com status de impedimento")
            
            with col3:
                metric("🎫 Total Geral", len(df_bugs_impedimentos), help_text="Total de bugs e impedimentos")
            
            st.markdown("---")
            
            # Tabela de Impedimentos
            st.subheader("🚫 Tabela de Impedimentos")
            
            # Preparar dados para a tabela
            df_impedimentos_table = df_bugs_impedimentos.copy()
            
            # Calcular Tempo Total (resolvido - created)
            df_impedimentos_table['Tempo Total (dias)'] = 0  # valor padrão
            
            # Calcular apenas para itens que têm ambas as datas
            mask_datas = (df_impedimentos_table['Data Criação'].notna() & 
                         df_impedimentos_table['Data Resolução'].notna())
            
            if mask_datas.any():
                df_impedimentos_table.loc[mask_datas, 'Tempo Total (dias)'] = (
                    pd.to_datetime(df_impedimentos_table.loc[mask_datas, 'Data Resolução']) - 
                    pd.to_datetime(df_impedimentos_table.loc[mask_datas, 'Data Criação'])
                ).dt.days
                
                # Para itens não resolvidos, calcular tempo até hoje
                mask_nao_resolvido = (df_impedimentos_table['Data Criação'].notna() & 
                                     df_impedimentos_table['Data Resolução'].isna())
                
                if mask_nao_resolvido.any():
                    # Usar datetime.now() sem timezone para evitar conflitos
                    from datetime import datetime
                    agora = pd.Timestamp(datetime.now())
                    datas_criacao = pd.to_datetime(df_impedimentos_table.loc[mask_nao_resolvido, 'Data Criação'])
                    
                    # Garantir que ambas as datas sejam timezone-naive
                    if agora.tz is not None:
                        agora = agora.tz_localize(None)
                    if hasattr(datas_criacao.dtype, 'tz') and datas_criacao.dtype.tz is not None:
                        datas_criacao = datas_criacao.dt.tz_localize(None)
                    
                    df_impedimentos_table.loc[mask_nao_resolvido, 'Tempo Total (dias)'] = (
                        agora - datas_criacao
                    ).dt.days
            
            # Selecionar e renomear colunas para a tabela
            colunas_tabela = {
                'Chave': 'Chave',
                'Resumo': 'Resumo', 
                'Status': 'Status',
                'Responsável': 'Agente Causador',
                'Tempo Total (dias)': 'Tempo Total (dias)'
            }
            
            df_tabela_final = df_impedimentos_table[list(colunas_tabela.keys())].rename(columns=colunas_tabela)
            
            # Ordenar por tempo total (decrescente)
            df_tabela_final = df_tabela_final.sort_values('Tempo Total (dias)', ascending=False)
            
            # Criar coluna com formato correto para LinkColumn (texto|url)
            df_tabela_final['Chave_Link'] = df_tabela_final['Chave'].apply(
                lambda x: f"{x}|{settings.JIRA_URL}/browse/{x}" if pd.notna(x) else ""
            )
            
            # Reorganizar colunas
            colunas_finais = ['Chave', 'Resumo', 'Status', 'Agente Causador', 'Tempo Total (dias)']
            df_tabela_final = df_tabela_final[colunas_finais]
            
            # Exibir tabela
            show_df(
                df_tabela_final,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config=build_column_config(colunas_finais)
            )
            
            # Estatísticas adicionais
            st.subheader("📈 Análise de Bugs & Impedimentos")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de distribuição por tipo
                tipo_counts = df_bugs_impedimentos['Tipo de Item'].value_counts()
                fig_tipos = pie(values=tipo_counts.values, names=tipo_counts.index, title="Distribuição por Tipo", color_sequence=['#dc3545', '#ffc107'])
                st.plotly_chart(fig_tipos, use_container_width=True)
            
            with col2:
                # Gráfico de tempo médio por tipo
                if 'Tempo Total (dias)' in df_impedimentos_table.columns:
                    tempo_medio = df_impedimentos_table.groupby('Tipo de Item')['Tempo Total (dias)'].mean().reset_index()
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
            st.markdown("""
            ### 🎉 Excelente!
            - Não há bugs registrados
            - Não há itens com status de impedimento
            - A sprint está seguindo sem bloqueios identificados
            """)
    
    # Início do bloco da Aba Story Points
    with tab6:
        st.subheader("📈 Análise de Story Points")
        
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
            st.subheader("🔍 Filtros")
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
            usar_historico = st.checkbox("Usar modo histórico por período (ignora sprints selecionadas)", value=False, help=None)
            if usar_historico:
                proj_key = st.session_state.get('projeto_key') or st.session_state.get('projeto')
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hist_inicio = st.date_input("Histórico - Criados a partir de:", value=data_inicio, help=None)
                with col_h2:
                    hist_fim = st.date_input("Histórico - Criados até:", value=data_resolucao_fim, help=None)
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
                        # Aplicar os mesmos filtros de tipos e SP > 0 (já garantidos pela JQL, mas reforçamos)
                        mask_tipos_hist = df_hist['Tipo de Item'].apply(lambda x: normalize(x) in tipos_validos_norm)
                        df_story_points = df_hist[mask_tipos_hist & (df_hist['Story Points'] > 0)].copy()
                        # Calcular dias
                        df_story_points = calc_dias(df_story_points, 'Data Criação', 'Data Resolução', out_col='Dias para Resolução')
                        # Reaplicar filtro de criação (a JQL já aplica, mantemos por segurança)
                        df_filtrado_sp = df_story_points.copy()
                        df_filtrado_sp = df_filtrado_sp[df_filtrado_sp['Data Criação'].notna()]
                        df_filtrado_sp = df_filtrado_sp[(df_filtrado_sp['Data Criação'].dt.date >= hist_inicio) & (df_filtrado_sp['Data Criação'].dt.date <= hist_fim)]
            
            # === SEÇÃO 2: MÉDIA POR STORY POINTS ===
            st.subheader("📊 Média de Dias por Story Points")
            
            # Calcular médias para story points específicos
            # Considerar SP usuais e incluir 21 quando presente
            sp_candidatos = STORY_POINTS_PADRAO
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
            story_points_valores = sp_presentes if sp_presentes else STORY_POINTS_PADRAO[:4]
            col_metrics = st.columns(len(story_points_valores) if story_points_valores else 1)
            
            df_resolvidos = df_filtrado_sp[df_filtrado_sp['Dias para Resolução'].notna()]
            
            for idx, sp_valor in enumerate(story_points_valores):
                with col_metrics[idx if story_points_valores else 0]:
                    df_sp_especifico = df_resolvidos[df_resolvidos['Story Points'] == sp_valor]
                    if not df_sp_especifico.empty:
                        media_dias = df_sp_especifico['Dias para Resolução'].mean()
                        total_itens = len(df_sp_especifico)
                        metric(label=f"📈 {sp_valor} SP", value=f"{media_dias:.1f} dias", delta=f"{total_itens} itens")
                    else:
                        metric(label=f"📈 {sp_valor} SP", value="Sem dados", delta="0 itens")
            
            # === SEÇÃO 2.1: TABELA DE MÉDIA POR TIPO E STORY POINTS ===
            st.subheader("📋 Média por Tipo e Story Points (Dias para Resolução)")
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
                agrupado = agrupado[agrupado['Story Points'].isin(story_points_valores)]
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

                # Cópia apenas para exibição com '—' onde NaN
                tabela_display = tabela.copy()
                for c in ['História', 'Débito Técnico', 'Spike']:
                    if c in tabela_display.columns:
                        tabela_display[c] = pd.to_numeric(tabela_display[c], errors='coerce').round(1)
                tabela_display = tabela_display.fillna('—')
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
                    
                    fig_media_sp = px.bar(media_por_sp, x='Story Points', y='Média Dias', title='Média de Dias por Story Points', text='Total Itens', color='Média Dias', color_continuous_scale='Viridis')
                    fig_media_sp.update_traces(textposition='outside')
                    fig_media_sp.update_layout(showlegend=False)
                    st.plotly_chart(fig_media_sp, use_container_width=True)
                else:
                    st.info("📊 Sem dados de resolução para gerar o gráfico")
            
            with col_graf2:
                # Gráfico de dispersão - Story Points vs Dias
                if not df_resolvidos.empty:
                    fig_scatter_sp = px.scatter(
                        df_resolvidos,
                        x='Story Points',
                        y='Dias para Resolução',
                        color='Tipo de Item',
                        title='Story Points vs Dias para Resolução',
                        hover_data=['Chave', 'Resumo']
                    )
                    st.plotly_chart(fig_scatter_sp, use_container_width=True)
                else:
                    st.info("📊 Sem dados de resolução para gerar o gráfico")
            
            # === SEÇÃO 4: TABELA DETALHADA ===
            st.subheader("📋 Dados Detalhados")
            
            # Preparar dados para exibição
            colunas_exibir = ['Chave', 'Resumo', 'Tipo de Item', 'Story Points', 'Status', 
                            'Responsável', 'Dias para Resolução']
            
            # Adicionar colunas de Sprint se múltiplas sprints
            if 'Sprint ID' in df_filtrado_sp.columns:
                colunas_exibir.insert(-1, 'Sprint ID')
            
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
            st.subheader("📈 Estatísticas Resumo")
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
            st.subheader("📋 Story Points x Média (dias) de Resolução")
            if not df_resolvidos.empty:
                df_tbl = df_resolvidos.copy()
                # Status concluído já garantido pela JQL, mas normalizamos SP
                df_tbl['Story Points'] = pd.to_numeric(df_tbl['Story Points'], errors='coerce')
                df_tbl = df_tbl.dropna(subset=['Story Points'])
                df_tbl['SP'] = df_tbl['Story Points'].astype(int)
                df_tbl = df_tbl[df_tbl['SP'].isin(sp_candidatos)]
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
                    st.info("Sem SP válidos (3, 5, 8, 13, 21) no período.")
            else:
                st.info("Sem itens resolvidos no período para calcular as médias.")

# Fim do bloco principal do dashboard

else:
    st.info("📊 Carregue os dados da sprint para visualizar as métricas e análises.")
    st.markdown("""
    ### 🚀 Como começar:
    1. **Configure a API:** Use a sidebar para inserir URL, email e token
    2. **Selecione o projeto:** Escolha o projeto Jira
    3. **Escolha a(s) sprint(s):** Selecione uma ou múltiplas sprints
    4. **Clique em "Carregar Dados"** para gerar o dashboard
    """)

# Footer
st.markdown("---")
st.markdown(
    "💡 **Dashboard desenvolvido para análise de sprints Jira** | "
    "🔧 Baseado em Streamlit e Plotly | "
    f"📅 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)