"""Builders para JQL padronizadas usadas no app."""


def _project_part(projeto_key: str) -> str:
    if projeto_key and projeto_key.isupper() and ' ' not in projeto_key:
        return f"project = {projeto_key}"
    return f'project = "{projeto_key}"'


def build_validate_project_jql(projeto_key: str) -> str:
    """JQL simples para validar existência de um projeto (traz 1 issue se existir)."""
    proj = _project_part(projeto_key)
    return f"{proj} ORDER BY created DESC"


def build_historico_jql(projeto_key: str, data_inicio: str, data_fim: str) -> str:
    """Monta a JQL de histórico conforme padrão acordado.

    Exemplo:
    project = SMD AND created >= "2025-06-10" AND created <= "2025-08-06 23:59" AND
    resolution IS NOT EMPTY AND status NOT IN (Cancelado) AND issuetype IN (Story, "Debito Tecnico", Spike)
    AND "Story Points[Number]" IS NOT EMPTY ORDER BY resolution DESC
    """
    proj = _project_part(projeto_key)
    return (
        f"{proj} AND created >= \"{data_inicio}\" "
        f"AND created <= \"{data_fim} 23:59\" "
        f"AND resolution IS NOT EMPTY AND status NOT IN (Cancelado) "
        f"AND issuetype IN (Story, \"Debito Tecnico\", Spike) "
        f"AND \"Story Points[Number]\" IS NOT EMPTY ORDER BY resolution DESC"
    )


def build_sprint_jql_variants(projeto: str, sprint_id: int, credcesta_special: bool = False) -> list[str]:
    """Retorna variantes de JQL para buscar issues de uma sprint.

    Mantém as mesmas opções usadas historicamente no cliente para compatibilidade.
    """
    if ' ' in projeto or '[' in projeto or ']' in projeto:
        proj = f'project = "{projeto}"'
    else:
        proj = f'project = {projeto}'

    if credcesta_special or 'credcesta' in (projeto or '').lower():
        return [
            f'{proj} AND cf[10020] = {sprint_id}',
            f'{proj} AND "cf[10020]" = {sprint_id}',
            f'{proj} AND customfield_10020 = {sprint_id}',
            f'{proj} AND "customfield_10020" = {sprint_id}',
        ]
    return [
        f'{proj} AND Sprint = {sprint_id}',
        f'{proj} AND "Sprint" = {sprint_id}',
        f'{proj} AND sprint = {sprint_id}',
        f'{proj} AND "Sprint" in ({sprint_id})',
        f'{proj} AND Sprint in ({sprint_id})',
        f'{proj} AND cf[10020] = {sprint_id}',
        f'{proj} AND cf[10010] = {sprint_id}',
    ]


