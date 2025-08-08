import pytest
import requests_mock
from jiraproject import sprint_service

@pytest.fixture
def mock_jira_issue():
    """Mock para a resposta da API de um issue do Jira."""
    return {
        "fields": {
            "customfield_12345": "Lorena Lima da Silveira dos Santos",
            "customfield_99999": "557058:abc123",  # Campo criptografado que deve ser ignorado
            "summary": "Teste de issue",
            "issuetype": {"name": "Story"},
            "status": {"name": "Done"},
            "assignee": {"displayName": "Outro User"},
            "customfield_10031": 5
        },
        "key": "SMD-2159"
    }

@pytest.fixture
def mock_sprint_data():
    """Mock para a resposta da API de uma sprint do Jira."""
    return {
        "total": 1,
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "summary": "Implementar feature X",
                    "issuetype": {"name": "História"},
                    "status": {"name": "Concluído"},
                    "assignee": {"displayName": "Lorena Lima da Silveira dos Santos"},
                    "customfield_10031": 8
                }
            }
        ]
    }

def test_descobrir_campo_responsavel():
    """Testa que a função sempre retorna 'assignee'."""
    campo = sprint_service.descobrir_campo_responsavel()
    assert campo == "assignee"

def test_processar_dados_sprint(mock_sprint_data):
    """Testa o processamento dos dados da sprint."""
    df = sprint_service.processar_dados_sprint(mock_sprint_data, "assignee")
    assert not df.empty
    assert df.iloc[0]['Responsável'] == "Lorena Lima da Silveira dos Santos"
    assert df.iloc[0]['Story Points'] == 8 