import pytest
import pandas as pd
from pathlib import Path
from typer.testing import CliRunner
from jiraproject.credcesta.cli import app

runner = CliRunner()

def test_analisar_cli_com_dados(mocker):
    """Testa o comando 'analisar' da CLI quando dados são retornados."""
    # Mock para retornar um DataFrame não vazio
    mock_df = pd.DataFrame({'Chave': ['PROJ-1']})
    mocker.patch("jiraproject.sprint_service.analisar_sprint", return_value=mock_df)
    
    # Mock para as funções de charts para evitar que gráficos sejam exibidos
    mocker.patch("jiraproject.charts.mostrar_distribuicao_por_tipo")
    mocker.patch("jiraproject.charts.mostrar_story_points_ageis")
    mocker.patch("jiraproject.charts.mostrar_distribuicao_responsaveis")
    mocker.patch("jiraproject.charts.mostrar_tempo_conclusao_story_points")
    
    result = runner.invoke(app, ["--projeto", "TEST", "--sprint", "1"])
    assert result.exit_code == 0
    assert "💾 Dados salvos em:" in result.stdout

def test_analisar_cli_sem_dados(mocker):
    """Testa o comando 'analisar' da CLI quando nenhum dado é retornado."""
    # Mock para retornar um DataFrame vazio
    mocker.patch("jiraproject.sprint_service.analisar_sprint", return_value=pd.DataFrame())
    
    result = runner.invoke(app, ["--projeto", "TEST", "--sprint", "1"])
    assert result.exit_code == 0
    assert "💾 Dados salvos em:" not in result.stdout

def test_analisar_cli_caracteres_especiais(mocker, tmp_path):
    """Testa o comando 'analisar' da CLI com caracteres especiais no nome do projeto."""
    # Muda para o diretório temporário
    original_cwd = Path.cwd()
    import os
    os.chdir(tmp_path)
    
    try:
        # Mock para retornar um DataFrame não vazio
        mock_df = pd.DataFrame({
            'Chave': ['PROJ-1'], 
            'Tipo de Item': ['História'],
            'Status': ['Done'],
            'Resumo': ['Test'],
            'Responsável': ['Test User'],
            'Story Points': [3]
        })
        mocker.patch("jiraproject.sprint_service.analisar_sprint", return_value=mock_df)
        
        # Mock para as funções de charts para evitar que gráficos sejam exibidos
        mocker.patch("jiraproject.charts.mostrar_distribuicao_por_tipo")
        mocker.patch("jiraproject.charts.mostrar_story_points_ageis")
        mocker.patch("jiraproject.charts.mostrar_distribuicao_responsaveis")
        mocker.patch("jiraproject.charts.mostrar_tempo_conclusao_story_points")
        
        # Testa com nome de projeto que contém caracteres especiais
        result = runner.invoke(app, ["--projeto", "[DIGITAL] Sites / Marketing", "--sprint", "4450"])
        
        assert result.exit_code == 0
        assert "💾 Dados salvos em:" in result.stdout
        
        # Verifica se o arquivo foi criado com nome sanitizado
        expected_filename = "DIGITAL_Sites_Marketing_4450_analysis.csv"
        assert Path(expected_filename).exists()
        
        # Verifica se o conteúdo do arquivo está correto
        df_saved = pd.read_csv(expected_filename)
        assert len(df_saved) == 1
        assert df_saved['Chave'].iloc[0] == 'PROJ-1'
        
    finally:
        # Restaura o diretório original
        os.chdir(original_cwd) 