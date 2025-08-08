import requests
from requests.auth import HTTPBasicAuth
from . import settings
from jiraproject.utils.jql import (
    build_validate_project_jql,
    build_historico_jql,
)
from jiraproject.utils.jira_fields import default_fields, sprint_fields, historico_fields
from jiraproject.utils.jql import build_sprint_jql_variants
from jiraproject.utils.log import info, ok, warn, error

def _get_auth():
    return HTTPBasicAuth(settings.JIRA_EMAIL, settings.JIRA_TOKEN)

def buscar_issue(issue_key: str):
    """Busca um issue específico no Jira."""
    url = f"{settings.JIRA_URL}/rest/api/3/issue/{issue_key}"
    try:
        response = requests.get(
            url,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error(f"Erro ao buscar issue {issue_key}: {e}")
        return None

def validar_projeto(projeto: str):
    """Valida se um projeto existe no Jira usando uma JQL padronizada via builder."""
    try:
        jql = build_validate_project_jql(projeto)
        issues = executar_jql(jql, max_results=1, fields='key')
        if issues:
            return True, f"Projeto '{projeto}' válido ({len(issues)} issues)"
        return False, f"Projeto '{projeto}' não encontrado"
    except Exception as e:
        return False, f"Erro ao validar projeto: {str(e)[:50]}..."

def buscar_sprints_do_board(board_id: int, limite: int = 10, filtro_nome: str = None):
    """Busca sprints de um board específico, priorizando a sprint ativa atual e as fechadas mais recentes.
    
    Args:
        board_id: ID do board
        limite: Número máximo de sprints FECHADAS recentes a retornar (além da ativa)
        filtro_nome: Filtrar sprints que contenham este texto no nome
    """
    base_url = f"{settings.JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint"

    def _filtra_nome(nome: str) -> bool:
        if not filtro_nome:
            return True
        return filtro_nome.lower() in (nome or '').lower()

    ativa = None
    fechadas = []

    try:
        # 1) Buscar sprint ATIVA (se houver)
        params_active = {
            'maxResults': 50,
            'state': 'active'
        }
        resp_active = requests.get(
            base_url,
            params=params_active,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        if resp_active.status_code == 200:
            values = resp_active.json().get('values', [])
            # Se houver múltiplas ativas (raro), escolher a mais recente por startDate/id
            if values:
                # aplicar filtro opcional de nome
                values = [s for s in values if _filtra_nome(s.get('name'))]
                if values:
                    values.sort(key=lambda s: (
                        s.get('startDate') or '',
                        s.get('id') or 0
                    ), reverse=True)
                    s = values[0]
                    ativa = {
                        'id': s.get('id'),
                        'nome': s.get('name'),
                        'estado': 'Ativa',
                        'inicio': s.get('startDate'),
                        'fim': s.get('endDate')
                    }
        # 2) Buscar sprints FECHADAS com paginação para garantir as mais recentes
        start_at = 0
        page_size = 50
        max_to_collect = max(limite * 3, 50)  # coletar mais do que o necessário para ordenar
        while len(fechadas) < max_to_collect:
            params_closed = {
                'maxResults': page_size,
                'startAt': start_at,
                'state': 'closed'
            }
            resp_closed = requests.get(
                base_url,
                params=params_closed,
                auth=_get_auth(),
                headers={'Accept': 'application/json'}
            )
            if resp_closed.status_code != 200:
                break
            data = resp_closed.json()
            values = data.get('values', [])
            if not values:
                break
            # Aplicar filtro por nome e acumular
            for s in values:
                nome = s.get('name', '')
                if not _filtra_nome(nome):
                    continue
                fechadas.append({
                    'id': s.get('id'),
                    'nome': nome,
                    'estado': 'Fechada',
                    'inicio': s.get('startDate'),
                    'fim': s.get('endDate'),
                    'completeDate': s.get('completeDate')
                })
            # Avançar paginação
            is_last = data.get('isLast', False)
            if is_last:
                break
            start_at += page_size
        # Ordenar fechadas por data de fim/completion mais recente
        def _orden_key(s):
            # usar completeDate, depois endDate, depois id
            return (
                s.get('completeDate') or s.get('fim') or '',
                s.get('id') or 0
            )
        fechadas.sort(key=_orden_key, reverse=True)
        recentes = fechadas[:limite]
        return {
            'ativa': ativa,
            'recentes': recentes
        }
    except requests.exceptions.RequestException as e:
        error(f"Erro ao buscar sprints do board {board_id}: {e}")
        return None

def listar_projetos(max_results: int = 1000):
    """Lista projetos disponíveis no Jira (key, id, name)."""
    url = f"{settings.JIRA_URL}/rest/api/3/project/search"
    params = {"maxResults": max_results}
    try:
        response = requests.get(
            url,
            params=params,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        data = response.json()
        values = data.get('values', []) or data.get('projects', []) or []
        projetos = [
            {
                'key': item.get('key'),
                'id': item.get('id'),
                'name': item.get('name')
            }
            for item in values
            if item.get('key') and item.get('name')
        ]
        return projetos
    except requests.exceptions.RequestException as e:
        error(f"Erro ao listar projetos: {e}")
        return []

def listar_squads(max_results: int = 1000, only_sprint_boards: bool = True):
    """Lista squads a partir dos boards Scrum do Jira.
    Retorna itens com: key (projectKey), name (projectName), board_name e board_id.
    """
    url = f"{settings.JIRA_URL}/rest/agile/1.0/board"
    params = {
        'type': 'scrum',
        'maxResults': max_results
    }
    try:
        response = requests.get(
            url,
            params=params,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        data = response.json()
        boards = data.get('values', [])
        squads_temp = {}
        for board in boards:
            location = board.get('location', {}) or {}
            project_key = (location.get('projectKey') or '').upper()
            project_name = location.get('projectName') or ''
            board_name = board.get('name') or ''
            board_id = board.get('id')
            if not project_key:
                continue
            if only_sprint_boards and '[SPRINT]' not in board_name.upper():
                # Guardar apenas se ainda não temos nenhuma opção para esta key
                if project_key in squads_temp:
                    continue
            # Preferir boards com [SPRINT] no nome
            current = squads_temp.get(project_key)
            prefer_current = current and ('[SPRINT]' in (current.get('board_name','').upper()))
            prefer_new = '[SPRINT]' in board_name.upper()
            if not current or (prefer_new and not prefer_current):
                squads_temp[project_key] = {
                    'key': project_key,
                    'name': project_name,
                    'board_name': board_name,
                    'board_id': board_id
                }
        # Ordenar pelo key
        squads = [squads_temp[k] for k in sorted(squads_temp.keys())]
        return squads
    except requests.exceptions.RequestException as e:
        error(f"Erro ao listar squads/boards: {e}")
        return []

def buscar_board_do_projeto(projeto: str):
    """Busca o board ID associado a um projeto."""
    url = f"{settings.JIRA_URL}/rest/agile/1.0/board"
    
    try:
        # Primeiro tentar buscar com filtro de projeto
        params = {
            'projectKeyOrId': projeto.upper(),  # Jira geralmente usa maiúsculas para project keys
            'maxResults': 100
        }
        
        response = requests.get(
            url,
            params=params,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        
        # Se deu erro 400, tentar sem filtro e buscar manualmente
        if response.status_code == 400:
            print(f"🔍 Tentativa 1 falhou, buscando todos os boards...")
            params = {'maxResults': 200}
            
            response = requests.get(
                url,
                params=params,
                auth=_get_auth(),
                headers={'Accept': 'application/json'}
            )
        
        if response.status_code == 200:
            data = response.json()
            boards = data.get('values', [])
            
            if boards:
                projeto_key_alvo = projeto.upper()
                melhor_match_exato = None
                melhor_match_nome = None
                primeiro_board = None
                for board in boards:
                    if primeiro_board is None:
                        primeiro_board = board
                    location = board.get('location', {}) or {}
                    project_key = (location.get('projectKey') or '').upper()
                    project_name = (location.get('projectName') or '')
                    board_name = (board.get('name') or '')
                    
                    # 1) Preferir casamento exato de projectKey e nome do board com [SPRINT]
                    if project_key == projeto_key_alvo:
                        if '[SPRINT]' in board_name.upper():
                            melhor_match_exato = board
                            break  # melhor possível
                        # guardar como candidato caso não haja com [SPRINT]
                        if melhor_match_exato is None:
                            melhor_match_exato = board
                    
                    # 2) Candidato por nome do projeto
                    if (projeto_key_alvo in project_name.upper()) or (project_name.upper() in projeto_key_alvo):
                        # preferir com [SPRINT]
                        if '[SPRINT]' in board_name.upper():
                            melhor_match_nome = board
                        elif melhor_match_nome is None:
                            melhor_match_nome = board
                
                escolhido = melhor_match_exato or melhor_match_nome or primeiro_board
                if escolhido:
                    ok(f"Board escolhido: {escolhido.get('name')} (ID: {escolhido.get('id')})")
                    return escolhido.get('id')
            else:
                warn(f"Nenhum board encontrado para o projeto '{projeto}'")
                return None
        else:
            error(f"Erro ao buscar board: HTTP {response.status_code}")
            if response.status_code == 400:
                warn(f"Erro 400: Verifique se o projeto '{projeto}' está correto")
            return None
            
    except requests.exceptions.RequestException as e:
        error(f"Erro de conexão ao buscar board: {e}")
        return None

def buscar_detalhes_sprint(sprint_id: int):
    """Busca detalhes de uma sprint específica (nome, datas, etc)."""
    url = f"{settings.JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}"
    
    try:
        response = requests.get(
            url,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar detalhes da sprint {sprint_id}: {e}")
        return None

def descobrir_campo_sprint():
    """Tenta descobrir qual campo representa 'Sprint' neste Jira."""
    url = f"{settings.JIRA_URL}/rest/api/3/field"
    
    try:
        response = requests.get(
            url,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        
        if response.status_code == 200:
            fields = response.json()
            
            # Procurar campos que podem ser Sprint
            sprint_fields = []
            for field in fields:
                field_name = field.get('name', '').lower()
                field_id = field.get('id', '')
                
                if 'sprint' in field_name:
                    sprint_fields.append({
                        'id': field_id,
                        'name': field.get('name'),
                        'custom': field.get('custom', False)
                    })
            
            info(f"Campos de Sprint encontrados: {sprint_fields}")
            return sprint_fields
        else:
            warn(f"Não foi possível descobrir campos de Sprint: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        warn(f"Erro ao descobrir campos: {e}")
        return []

def buscar_sprint_jira(projeto: str, sprint_id: int, campo_responsavel: str = 'assignee'):
    """Busca dados de uma sprint específica no Jira."""
    # Usar builder padronizado de variantes
    jql_variants = build_sprint_jql_variants(projeto, sprint_id)
    
    # Tentar cada variante de JQL
    for i, jql in enumerate(jql_variants):
        jql_final = f'{jql} ORDER BY cf[10031] ASC'
        info(f"Tentativa {i+1}: {jql_final}")
        
        result = _executar_busca_jql(jql_final, sprint_id)
        if result is not None:
            return result
    
    error(f"Todas as tentativas de JQL falharam para sprint {sprint_id}")
    return None

def _executar_busca_jql(jql: str, sprint_id: int):
    """Executa uma busca JQL específica."""
    url = f"{settings.JIRA_URL}/rest/api/3/search"
    
    # Sempre inclui apenas os campos necessários (padronizados)
    fields_busca = sprint_fields()

    params = {
        'jql': jql,
        'maxResults': 100,
        'fields': fields_busca
    }
    
    try:
        response = requests.get(
            url,
            params=params,
            auth=_get_auth(),
            headers={'Accept': 'application/json'}
        )
        
        # Se deu erro 400, não é esta variante de JQL
        if response.status_code == 400:
            return None
            
        response.raise_for_status()
        result = response.json()
        
        # Verifica se encontrou issues
        if result.get('total', 0) == 0:
            warn(f"Nenhum issue encontrado com esta JQL")
            return None
            
        ok(f"Total de issues encontradas: {result.get('total', 0)}")
        return result
        
    except requests.exceptions.RequestException as e:
        # Para erro 400, apenas retorna None (tentará próxima variante)
        if hasattr(e, 'response') and e.response and e.response.status_code == 400:
            return None
        
        # Outros erros, reporta
        error(f"Erro na busca: {e}")
        return None

def executar_jql(jql: str, max_results: int = 2000, fields: str = None):
    """Executor genérico de JQL: retorna lista de issues.

    Args:
        jql: consulta JQL completa
        max_results: máximo de resultados a coletar (com paginação)
        fields: lista de campos (string separada por vírgula). Se None, usa um conjunto padrão amplo.
    """
    url = f"{settings.JIRA_URL}/rest/api/3/search"
    if not fields:
        fields = default_fields()

    start_at = 0
    page_size = 100
    coletadas = []
    try:
        while start_at < max_results:
            params = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': min(page_size, max_results - start_at),
                'fields': fields
            }
            response = requests.get(
                url,
                params=params,
                auth=_get_auth(),
                headers={'Accept': 'application/json'}
            )
            if response.status_code == 400:
                warn(f"JQL inválida: {jql}")
                break
            response.raise_for_status()
            data = response.json()
            issues = data.get('issues', [])
            coletadas.extend(issues)
            if len(issues) < params['maxResults']:
                break
            start_at += params['maxResults']
        return coletadas
    except requests.exceptions.RequestException as e:
        error(f"Erro ao executar JQL: {e}")
        return []

def buscar_issues_por_periodo(projeto_key: str, data_inicio: str, data_fim: str, max_results: int = 2000):
    """Busca issues concluídos com Story Points preenchidos por período via builder/exec genérico."""
    jql = build_historico_jql(projeto_key, data_inicio, data_fim)
    fields = historico_fields()
    issues = executar_jql(jql, max_results=max_results, fields=fields)
    ok(f"Histórico coletado: {len(issues)} issues {data_inicio}..{data_fim} ({projeto_key})")
    return issues
