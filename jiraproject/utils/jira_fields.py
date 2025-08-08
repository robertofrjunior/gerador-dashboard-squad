"""Listas padronizadas de campos do Jira usadas nas consultas JQL."""

from typing import List


def default_fields_list() -> List[str]:
    return [
        'key', 'summary', 'issuetype', 'status', 'assignee',
        'created', 'resolved', 'resolutiondate', 'resolution',
        'customfield_10016',  # Story Points (vários Jira usam 10016)
        'customfield_10026',  # Epic Link / outros
        'customfield_10031',  # Responsável Oficial / Ordenação
        'customfield_10010',  # Sprint (comum)
    ]


def default_fields() -> str:
    return ','.join(default_fields_list())


def sprint_fields() -> str:
    # Sprint precisa de created/resolutiondate + campo de ordenação 10031
    campos = list({
        *default_fields_list(),
        'priority',  # usado em telas de sprint
    })
    return ','.join(campos)


def historico_fields() -> str:
    # Históricos focam em datas e SPs
    campos = list({
        *default_fields_list(),
    })
    return ','.join(campos)


