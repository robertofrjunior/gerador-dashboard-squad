import pytest
import requests_mock
from credcesta import jira_client, settings

def test_buscar_issue(requests_mock):
    """Testa a busca de um issue específico."""
    requests_mock.get(f"{settings.JIRA_URL}/rest/api/3/issue/TEST-1", json={"key": "TEST-1"})
    issue = jira_client.buscar_issue("TEST-1")
    assert issue is not None
    assert issue['key'] == "TEST-1"

def test_buscar_sprint_jira(requests_mock):
    """Testa a busca de dados de uma sprint."""
    # Retorna pelo menos um issue para a primeira JQL de tentativa
    requests_mock.get(
        f"{settings.JIRA_URL}/rest/api/3/search",
        json={"total": 1, "issues": [{"key": "PROJ-123"}]}
    )
    data = jira_client.buscar_sprint_jira("PROJ", 123, "customfield_12345")
    assert data is not None
    assert data['total'] >= 1