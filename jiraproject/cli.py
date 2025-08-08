import typer
from pathlib import Path
from jiraproject import sprint_service
from jiraproject.credcesta import charts
from jiraproject import sanitize_filename

app = typer.Typer()

@app.command()
def analisar(
    projeto: str = typer.Option(..., "--projeto", "-p", help="Nome do projeto no Jira"),
    sprint: int = typer.Option(..., "--sprint", "-s", help="ID da Sprint para análise"),
):
    """
    Analisa uma sprint do Jira e exibe métricas e gráficos.
    """
    df_sprint = sprint_service.analisar_sprint(projeto, sprint)
    
    if not df_sprint.empty:
        charts.mostrar_distribuicao_por_tipo(df_sprint)
        charts.mostrar_story_points_ageis(df_sprint)
        charts.mostrar_tempo_conclusao_story_points(df_sprint)
        
        charts.mostrar_distribuicao_responsaveis(df_sprint)
        
        filename = sanitize_filename(f"{projeto}_{sprint}_analysis.csv")
        
        # Garante que o diretório pai existe
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        df_sprint.to_csv(filename, index=False)
        print(f"\n💾 Dados salvos em: {filename}")
