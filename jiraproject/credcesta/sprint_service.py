import pandas as pd
import warnings
from . import jira_client

def descobrir_campo_responsavel():
    """
    Retorna o campo 'assignee' como campo responsável.
    
    O campo 'assignee' é o campo padrão do Jira para atribuição de issues
    e contém o responsável pela issue.
    
    Returns:
        str: Sempre retorna 'assignee'
    """
    return 'assignee'

def processar_dados_sprint(data, campo_responsavel='assignee'):
    """Processa os dados da sprint para um DataFrame."""
    if not data or 'issues' not in data:
        return pd.DataFrame()
        
    dados = []
    for issue in data['issues']:
        fields = issue['fields']
        
        # Extrai responsável do campo assignee
        responsavel = "Não atribuído"
        if fields.get('assignee'):
            responsavel = fields['assignee'].get('displayName', 'Não identificado')

        tipo_item = fields['issuetype']['name']
        # Sempre pegar o valor de Story Points, independente do tipo
        story_points = fields.get('customfield_10031', 0) or 0
            
        dados.append({
            'Chave': issue['key'],
            'Tipo de Item': tipo_item,
            'Status': fields['status']['name'],
            'Resumo': fields.get('summary', ''),
            'Responsável': responsavel,
            'Story Points': story_points,
            'Data Criação': fields.get('created'),
            'Data Resolução': fields.get('resolutiondate')
        })

    # Converte lista em DataFrame
    df = pd.DataFrame(dados)
    # Converte campos de data para datetime
    if not df.empty:
        df['Data Criação'] = pd.to_datetime(df['Data Criação'], errors='coerce')
        df['Data Resolução'] = pd.to_datetime(df['Data Resolução'], errors='coerce')
    return df


def analisar_sprint(projeto: str, sprint_id: int):
    """Análise completa de uma sprint."""
    campo_responsavel = descobrir_campo_responsavel()
    
    # Buscar detalhes da sprint (nome, datas)
    detalhes_sprint = jira_client.buscar_detalhes_sprint(sprint_id)
    
    # Buscar issues da sprint
    data_sprint = jira_client.buscar_sprint_jira(projeto, sprint_id, campo_responsavel)
    
    if data_sprint:
        total_issues = data_sprint.get('total', 0)
        print(f"✅ Total de issues na sprint: {total_issues}")
        if total_issues > 0:
            df_result = processar_dados_sprint(data_sprint, campo_responsavel)
            # Adiciona informação do total para uso posterior
            df_result.attrs['total_sprint'] = total_issues
            
            # Adiciona detalhes da sprint se disponíveis
            if detalhes_sprint:
                df_result.attrs['sprint_nome'] = detalhes_sprint.get('name', f'Sprint {sprint_id}')
                df_result.attrs['sprint_inicio'] = detalhes_sprint.get('startDate')
                df_result.attrs['sprint_fim'] = detalhes_sprint.get('endDate')
                df_result.attrs['sprint_estado'] = detalhes_sprint.get('state')
            else:
                df_result.attrs['sprint_nome'] = f'Sprint {sprint_id}'
                df_result.attrs['sprint_inicio'] = None
                df_result.attrs['sprint_fim'] = None
                df_result.attrs['sprint_estado'] = None
                
            return df_result
    
    print("❌ Erro ao buscar dados da sprint")
    return pd.DataFrame()
