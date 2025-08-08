#!/usr/bin/env python3
"""Script de debug para encontrar o campo responsável correto."""

from jiraproject import jira_client
import json

def analisar_issue(issue_key):
    """Analisa uma issue e mostra todos os campos customizados com valores."""
    print(f"\n🔍 Analisando issue: {issue_key}")
    print("=" * 80)
    
    issue_data = jira_client.buscar_issue(issue_key)
    if not issue_data:
        print("❌ Não foi possível buscar a issue")
        return
    
    fields = issue_data.get('fields', {})
    
    # Primeiro, mostra campos padrão importantes
    print("\n📋 CAMPOS PADRÃO:")
    print(f"  - Assignee: {fields.get('assignee', {}).get('displayName', 'Não atribuído') if fields.get('assignee') else 'Não atribuído'}")
    print(f"  - Reporter: {fields.get('reporter', {}).get('displayName', 'N/A') if fields.get('reporter') else 'N/A'}")
    print(f"  - Creator: {fields.get('creator', {}).get('displayName', 'N/A') if fields.get('creator') else 'N/A'}")
    
    # Agora analisa campos customizados
    print("\n🔧 CAMPOS CUSTOMIZADOS:")
    campos_com_nomes = []
    campos_com_datas = []
    outros_campos = []
    
    for field_key, field_value in sorted(fields.items()):
        if field_key.startswith('customfield_') and field_value is not None:
            # Tenta extrair o valor de exibição
            valor_display = None
            tipo_campo = "desconhecido"
            
            if isinstance(field_value, dict):
                if 'displayName' in field_value:
                    valor_display = field_value['displayName']
                    tipo_campo = "usuário"
                elif 'name' in field_value:
                    valor_display = field_value['name']
                    tipo_campo = "objeto"
                elif 'value' in field_value:
                    valor_display = field_value['value']
                    tipo_campo = "seleção"
                else:
                    valor_display = str(field_value)
                    tipo_campo = "dict"
            elif isinstance(field_value, str):
                valor_display = field_value
                # Detecta se é uma data
                if 'T' in field_value and ':' in field_value:
                    tipo_campo = "data"
                else:
                    tipo_campo = "texto"
            elif isinstance(field_value, list):
                if field_value and isinstance(field_value[0], dict):
                    valores = [item.get('displayName', item.get('name', str(item))) for item in field_value]
                    valor_display = ', '.join(valores)
                    tipo_campo = "lista"
                else:
                    valor_display = str(field_value)
                    tipo_campo = "lista"
            else:
                valor_display = str(field_value)
                tipo_campo = type(field_value).__name__
            
            # Categoriza o campo
            if tipo_campo == "data":
                campos_com_datas.append((field_key, valor_display, tipo_campo))
            elif tipo_campo == "usuário" or (valor_display and ' ' in str(valor_display) and any(c.isalpha() for c in str(valor_display))):
                campos_com_nomes.append((field_key, valor_display, tipo_campo))
            else:
                outros_campos.append((field_key, valor_display, tipo_campo))
    
    # Exibe campos categorizados
    if campos_com_nomes:
        print("\n  👤 Campos que parecem conter NOMES/USUÁRIOS:")
        for field_key, valor, tipo in campos_com_nomes:
            print(f"    - {field_key}: '{valor}' (tipo: {tipo})")
    
    if campos_com_datas:
        print("\n  📅 Campos que parecem conter DATAS:")
        for field_key, valor, tipo in campos_com_datas:
            print(f"    - {field_key}: '{valor}' (tipo: {tipo})")
    
    if outros_campos:
        print("\n  📦 Outros campos:")
        for field_key, valor, tipo in outros_campos[:10]:  # Limita a 10 para não poluir
            print(f"    - {field_key}: '{valor}' (tipo: {tipo})")
    
    # Recomendação
    if campos_com_nomes:
        campo_recomendado = campos_com_nomes[0][0]
        print(f"\n✅ RECOMENDAÇÃO: Use o campo '{campo_recomendado}' para responsável")
        print(f"   Valor encontrado: '{campos_com_nomes[0][1]}'")
    else:
        print("\n⚠️  AVISO: Nenhum campo customizado com nome de usuário foi encontrado!")
        print("   Talvez o responsável esteja no campo 'assignee' padrão")

# Analisa as issues de referência
if __name__ == "__main__":
    for issue_key in ["SMD-2159", "SMD-2170", "SMD-2180"]:
        analisar_issue(issue_key)