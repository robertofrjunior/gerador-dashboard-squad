"""Serviços de integração ao Jira (fachada)."""
from typing import Optional
from jiraproject import jira_client as _client
from jiraproject.utils.jira_fields import sprint_fields, historico_fields
from jiraproject.utils.jql import build_historico_jql, build_validate_project_jql
from jiraproject.utils.jql import build_sprint_jql_variants
from jiraproject.utils.log import info, ok, warn, error


def listar_projetos():
    return _client.listar_projetos()


def listar_squads():
    return _client.listar_squads()


def validar_projeto(nome: str):
    # Primeiro via JQL simples; se falhar, usar método antigo
    jql = build_validate_project_jql(nome)
    info(f"Validando projeto via JQL: {jql}")
    issues = _client.executar_jql(jql, max_results=1, fields='key')
    if issues:
        ok(f"Projeto '{nome}' válido")
        return True, f"Projeto '{nome}' válido"
    return _client.validar_projeto(nome)


def buscar_board_do_projeto(projeto: str) -> Optional[int]:
    return _client.buscar_board_do_projeto(projeto)


def buscar_sprints_do_board(board_id: int, limite: int = 10, filtro_nome: Optional[str] = None):
    return _client.buscar_sprints_do_board(board_id, limite=limite, filtro_nome=filtro_nome)


def buscar_issues_por_periodo(projeto_key: str, data_inicio: str, data_fim: str, max_results: int = 2000):
    # Monta JQL padronizada e executa via cliente
    jql = build_historico_jql(projeto_key, data_inicio, data_fim)
    info(f"Histórico JQL: {jql}")
    return _client.executar_jql(jql, max_results=max_results, fields=historico_fields())


def buscar_sprint_jira(projeto: str, sprint_id: int):
    variants = build_sprint_jql_variants(projeto, sprint_id)
    for i, jql in enumerate(variants, start=1):
        jql_final = f"{jql} ORDER BY cf[10031] ASC"
        info(f"Tentativa {i}: {jql_final}")
        result = _client.executar_jql(jql_final, max_results=100, fields=sprint_fields())
        if result:
            # Adaptar para contrato antigo: empacotar em dict com total
            ok(f"Sprint {sprint_id}: {len(result)} issues")
            return {"total": len(result), "issues": result}
    error(f"Todas as tentativas de JQL falharam para sprint {sprint_id}")
    return None


