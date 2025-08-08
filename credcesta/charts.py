import matplotlib.pyplot as plt

def mostrar_distribuicao_por_tipo(df):
    """Gera gráfico de distribuição por tipo de item."""
    print("\n📊 DISTRIBUIÇÃO POR TIPO DE ITEM:")
    tipos_ageis = ['Debito Tecnico', 'História', 'Spike']
    df_filtrado = df[df['Tipo de Item'].isin(tipos_ageis)]
    
    if df_filtrado.empty:
        print("   Nenhum item dos tipos ágeis encontrado.")
        return
    
    tipo_counts = df_filtrado['Tipo de Item'].value_counts()
    for tipo, count in tipo_counts.items():
        print(f"   {tipo}: {count}")
    
    plt.figure(figsize=(8, 5))
    bars = tipo_counts.plot(kind='bar', color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
    plt.title('Distribuição por Tipo de Item (Framework Ágil)', fontsize=14)
    plt.ylabel('Quantidade de Itens')
    plt.xlabel('Tipo de Item')
    plt.xticks(rotation=45)
    for bar in bars.patches:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    plt.tight_layout()
    plt.show()

def mostrar_story_points_ageis(df):
    """Gera gráficos de Story Points."""
    tipos_ageis = ['História', 'Debito Tecnico', 'Spike']
    df_ageis = df[df['Tipo de Item'].isin(tipos_ageis)]
    
    status_concluidos = ['Concluído', 'Done', 'Fechado', 'Finalizado', 'Resolvido']
    df_concluidos_ageis = df_ageis[df_ageis['Status'].isin(status_concluidos)]
    
    total_sp = df_ageis['Story Points'].sum()
    sp_concluidos = df_concluidos_ageis['Story Points'].sum()
    
    print(f"\n🎯 STORY POINTS (APENAS ITENS ÁGEIS):")
    print(f"   Total planejado: {total_sp}")
    print(f"   Total concluído: {sp_concluidos}")
    print(f"   % Concluído: {(sp_concluidos/total_sp*100):.1f}%" if total_sp > 0 else "N/A")

    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    plt.bar(['Planejado', 'Concluído'], [total_sp, sp_concluidos], color=['#74B9FF', '#00B894'])
    plt.title('Story Points: Planejado vs Concluído')
    plt.ylabel('Story Points')
    for i, v in enumerate([total_sp, sp_concluidos]):
        plt.text(i, v + max(total_sp, sp_concluidos) * 0.01, str(v), ha='center', va='bottom', fontweight='bold')

    df_com_sp = df_ageis[df_ageis['Story Points'] > 0]
    if not df_com_sp.empty:
        plt.subplot(1, 2, 2)
        sp_por_tipo = df_com_sp.groupby('Tipo de Item')['Story Points'].sum()
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        bars = plt.bar(sp_por_tipo.index, sp_por_tipo.values, color=colors[:len(sp_por_tipo)])
        plt.title('Story Points por Tipo de Item')
        plt.ylabel('Story Points')
        plt.xticks(rotation=45)
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + height * 0.01, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.show()

def mostrar_distribuicao_responsaveis(df, total_sprint=None):
    """Gera gráficos de distribuição de itens por responsável."""
    tipos_ageis = ['História', 'Debito Tecnico', 'Spike']
    df_ageis = df[df['Tipo de Item'].isin(tipos_ageis)]
    
    print(f"\n👥 DISTRIBUIÇÃO DE ITENS POR RESPONSÁVEL (ITENS ÁGEIS):")
    responsavel_counts = df_ageis['Responsável'].value_counts()
    total_ageis = len(df_ageis)
    
    for responsavel, count in responsavel_counts.items():
        pct_ageis = (count / total_ageis * 100) if total_ageis > 0 else 0
        if total_sprint:
            pct_total = (count / total_sprint * 100) if total_sprint > 0 else 0
            print(f"   {responsavel}: {count} itens ({pct_ageis:.1f}% dos ágeis, {pct_total:.1f}% do total da sprint)")
        else:
            print(f"   {responsavel}: {count} itens ({pct_ageis:.1f}% dos ágeis)")
    
    print(f"\n📊 ESTATÍSTICAS DE DISTRIBUIÇÃO:")
    print(f"   Total de itens ágeis: {total_ageis}")
    if total_sprint:
        print(f"   Total de itens na sprint: {total_sprint}")
        pct_ageis_na_sprint = (total_ageis / total_sprint * 100) if total_sprint > 0 else 0
        print(f"   Itens ágeis representam {pct_ageis_na_sprint:.1f}% da sprint")
        
        # Pivot table com todos os tipos de itens x responsáveis
        print(f"\n📋 PIVOT TABLE: TIPOS DE ITENS × RESPONSÁVEIS (TODA A SPRINT)")
        pivot_table = df.pivot_table(
            index='Tipo de Item', 
            columns='Responsável', 
            values='Chave', 
            aggfunc='count', 
            fill_value=0
        )
        
        # Formatar a saída da pivot table
        if not pivot_table.empty:
            # Criar cabeçalho
            responsaveis = list(pivot_table.columns)
            tipos = list(pivot_table.index)
            
            # Calcular larguras para formatação
            max_tipo_len = max(len(str(tipo)) for tipo in tipos) + 2
            max_resp_len = max(6, max(len(str(resp)[:10]) for resp in responsaveis))
            
            # Cabeçalho
            header = f"{'Tipo de Item':<{max_tipo_len}}"
            for resp in responsaveis:
                resp_short = str(resp)[:10] + '...' if len(str(resp)) > 10 else str(resp)
                header += f"{resp_short:>{max_resp_len+2}}"
            header += f"{'Total':>{max_resp_len+2}}"
            print(f"   {header}")
            print(f"   {'-' * len(header)}")
            
            # Dados
            for tipo in tipos:
                linha = f"{str(tipo):<{max_tipo_len}}"
                total_linha = 0
                for resp in responsaveis:
                    valor = pivot_table.loc[tipo, resp]
                    linha += f"{valor:>{max_resp_len+2}}"
                    total_linha += valor
                linha += f"{total_linha:>{max_resp_len+2}}"
                print(f"   {linha}")
            
            # Totais por coluna
            linha_total = f"{'TOTAL':<{max_tipo_len}}"
            grand_total = 0
            for resp in responsaveis:
                total_col = pivot_table[resp].sum()
                linha_total += f"{total_col:>{max_resp_len+2}}"
                grand_total += total_col
            linha_total += f"{grand_total:>{max_resp_len+2}}"
            print(f"   {'-' * len(header)}")
            print(f"   {linha_total}")
        else:
            print("   Nenhum dado disponível para pivot table")
            
        # Gera gráfico da pivot table automaticamente
        print(f"\n🎨 Gerando gráfico da pivot table...")
        mostrar_grafico_pivot_table(df)
        
        # Mostra opções de filtros para uso futuro
        mostrar_opcoes_filtros(df)

    if not responsavel_counts.empty:
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        colors = plt.cm.Set3(range(len(responsavel_counts)))
        
        bars = ax[0].bar(range(len(responsavel_counts)), responsavel_counts.values, color=colors)
        titulo = f'Distribuição de Itens Ágeis por Responsável'
        if total_sprint:
            titulo += f' ({total_ageis}/{total_sprint} total)'
        ax[0].set_title(titulo)
        ax[0].set_xticks(range(len(responsavel_counts)))
        ax[0].set_xticklabels([str(nome)[:15] + '...' if len(str(nome)) > 15 else str(nome) for nome in responsavel_counts.index], rotation=45, ha='right')

        ax[1].pie(responsavel_counts.values, labels=[str(nome)[:10] + '...' if len(str(nome)) > 10 else str(nome) for nome in responsavel_counts.index], autopct='%1.1f%%', startangle=90, colors=colors)
        ax[1].set_title('Proporção de Itens Ágeis por Responsável')
        
        plt.tight_layout()
        plt.show()

def mostrar_grafico_pivot_table(df, filtro_status=None, filtro_tipo=None):
    """
    Gera gráfico de barras da pivot table com filtros opcionais.
    
    Args:
        df: DataFrame com os dados da sprint
        filtro_status: Lista de status para filtrar (ex: ['Concluído', 'Done'])
        filtro_tipo: Lista de tipos para filtrar (ex: ['História', 'Bug'])
    """
    print(f"\n📊 GRÁFICO PIVOT TABLE: TIPOS DE ITENS × RESPONSÁVEIS")
    
    # Aplicar filtros se especificados
    df_filtrado = df.copy()
    
    if filtro_status:
        df_filtrado = df_filtrado[df_filtrado['Status'].isin(filtro_status)]
        print(f"   🔍 Filtro Status: {', '.join(filtro_status)}")
    
    if filtro_tipo:
        df_filtrado = df_filtrado[df_filtrado['Tipo de Item'].isin(filtro_tipo)]
        print(f"   🔍 Filtro Tipo: {', '.join(filtro_tipo)}")
        
    if df_filtrado.empty:
        print("   ❌ Nenhum dado encontrado com os filtros aplicados")
        return
    
    # Criar pivot table
    pivot_table = df_filtrado.pivot_table(
        index='Tipo de Item', 
        columns='Responsável', 
        values='Chave', 
        aggfunc='count', 
        fill_value=0
    )
    
    if pivot_table.empty:
        print("   ❌ Não foi possível criar pivot table com os dados filtrados")
        return
    
    # Preparar dados para o gráfico
    tipos = list(pivot_table.index)
    responsaveis = list(pivot_table.columns)
    
    # Criar figura com subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    
    # Gráfico 1: Barras agrupadas por tipo de item
    x_pos = range(len(tipos))
    width = 0.8 / len(responsaveis) if len(responsaveis) > 0 else 0.8
    colors = plt.cm.Set3(range(len(responsaveis)))
    
    for i, resp in enumerate(responsaveis):
        valores = [pivot_table.loc[tipo, resp] for tipo in tipos]
        resp_label = str(resp)[:12] + '...' if len(str(resp)) > 12 else str(resp)
        ax1.bar([x + i * width for x in x_pos], valores, width, 
                label=resp_label, color=colors[i], alpha=0.8)
    
    ax1.set_xlabel('Tipo de Item')
    ax1.set_ylabel('Quantidade de Itens')
    titulo1 = 'Distribuição por Tipo de Item e Responsável'
    if filtro_status or filtro_tipo:
        titulo1 += ' (Filtrado)'
    ax1.set_title(titulo1)
    ax1.set_xticks([x + width * (len(responsaveis) - 1) / 2 for x in x_pos])
    ax1.set_xticklabels([str(tipo)[:15] + '...' if len(str(tipo)) > 15 else str(tipo) 
                         for tipo in tipos], rotation=45, ha='right')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(axis='y', alpha=0.3)
    
    # Gráfico 2: Barras empilhadas por responsável
    bottom_values = [0] * len(responsaveis)
    
    for i, tipo in enumerate(tipos):
        valores = [pivot_table.loc[tipo, resp] for resp in responsaveis]
        tipo_label = str(tipo)[:12] + '...' if len(str(tipo)) > 12 else str(tipo)
        ax2.bar(range(len(responsaveis)), valores, bottom=bottom_values,
                label=tipo_label, color=plt.cm.Set2(i), alpha=0.8)
        bottom_values = [b + v for b, v in zip(bottom_values, valores)]
    
    ax2.set_xlabel('Responsável')
    ax2.set_ylabel('Quantidade de Itens')
    titulo2 = 'Distribuição por Responsável (Empilhado)'
    if filtro_status or filtro_tipo:
        titulo2 += ' (Filtrado)'
    ax2.set_title(titulo2)
    ax2.set_xticks(range(len(responsaveis)))
    ax2.set_xticklabels([str(resp)[:12] + '...' if len(str(resp)) > 12 else str(resp) 
                         for resp in responsaveis], rotation=45, ha='right')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.grid(axis='y', alpha=0.3)
    
    # Estatísticas
    total_itens = df_filtrado.shape[0]
    print(f"   📈 Total de itens no gráfico: {total_itens}")
    print(f"   📋 Tipos únicos: {len(tipos)}")
    print(f"   👥 Responsáveis únicos: {len(responsaveis)}")
    
    plt.tight_layout()
    plt.show()

def mostrar_opcoes_filtros(df):
    """
    Mostra as opções disponíveis para filtros de Status e Tipo de Item.
    """
    print(f"\n🔧 OPÇÕES DISPONÍVEIS PARA FILTROS:")
    
    # Status únicos
    status_unicos = sorted(df['Status'].unique())
    print(f"\n   📊 Status disponíveis ({len(status_unicos)}):")
    for i, status in enumerate(status_unicos, 1):
        print(f"      {i}. {status}")
    
    # Tipos únicos
    tipos_unicos = sorted(df['Tipo de Item'].unique())
    print(f"\n   📋 Tipos de Item disponíveis ({len(tipos_unicos)}):")
    for i, tipo in enumerate(tipos_unicos, 1):
        print(f"      {i}. {tipo}")
    
    print(f"\n   💡 Para usar filtros, chame:")
    print(f"      mostrar_grafico_pivot_table(df, filtro_status=['Concluído', 'Done'])")
    print(f"      mostrar_grafico_pivot_table(df, filtro_tipo=['História', 'Bug'])")
    print(f"      mostrar_grafico_pivot_table(df, filtro_status=['Done'], filtro_tipo=['História'])")


def mostrar_tempo_conclusao_story_points(df):
    """Gera gráfico de tempo de conclusão para itens com Story Points preenchidos."""
    # Filtra itens que possuem Story Points > 0 e datas válidas
    df_sp = df[(df['Story Points'] > 0)].copy()

    # Verifica se as colunas necessárias existem
    if 'Data Criação' not in df_sp.columns or 'Data Resolução' not in df_sp.columns:
        print("⚠️  Colunas de data não encontradas no DataFrame. Certifique-se de que 'Data Criação' e 'Data Resolução' estejam presentes.")
        return

    # Remove linhas com datas nulas
    df_sp.dropna(subset=['Data Criação', 'Data Resolução'], inplace=True)

    if df_sp.empty:
        print("❌ Nenhum item com Story Points e datas de criação/resolução válidas encontrado.")
        return

    # Calcula a diferença em dias entre criação e resolução
    df_sp['Dias para Conclusão'] = (df_sp['Data Resolução'] - df_sp['Data Criação']).dt.days

    dias_values = df_sp['Dias para Conclusão']

    media_dias = dias_values.mean()
    print(f"\n⏱️  TEMPO DE CONCLUSÃO (ITENS COM STORY POINTS)")
    print(f"   Total de itens considerados: {len(dias_values)}")
    print(f"   Tempo médio de conclusão (todos os tipos): {media_dias:.2f} dias")
    print(f"   Tempo mínimo: {dias_values.min()} dias | Tempo máximo: {dias_values.max()} dias")

    # Média por tipo de item (História, Débito Técnico, Spike)
    tipos_ageis = ['História', 'Debito Tecnico', 'Spike']
    medias_por_tipo = (df_sp[df_sp['Tipo de Item'].isin(tipos_ageis)]
                       .groupby('Tipo de Item')['Dias para Conclusão']
                       .mean()
                       .sort_index())

    if not medias_por_tipo.empty:
        print("\n📊 Dias médios para conclusão por Tipo de Item:")
        for tipo, dias in medias_por_tipo.items():
            print(f"   {tipo}: {dias:.2f} dias")

        # Gráfico de barras com médias por tipo
        plt.figure(figsize=(8, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        bars_medias = plt.bar(medias_por_tipo.index, medias_por_tipo.values, color=colors[:len(medias_por_tipo)])
        plt.title('Dias Médios para Conclusão por Tipo de Item (Story Points > 0)')
        plt.ylabel('Dias')
        plt.xlabel('Tipo de Item')
        plt.xticks(rotation=45)
        for bar in bars_medias:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01, f'{height:.1f}', ha='center', va='bottom', fontweight='bold')
        plt.tight_layout()
        plt.show()

    # Gera histograma
    plt.figure(figsize=(10, 5))
    n, bins, patches = plt.hist(dias_values, bins=range(int(dias_values.min()), int(dias_values.max()) + 2), color='#0984e3', alpha=0.7, rwidth=0.85)
    plt.title('Distribuição de Dias para Conclusão (itens com Story Points)')
    plt.xlabel('Dias para Conclusão')
    plt.ylabel('Quantidade de Itens')

    # Adiciona rótulos em cada barra
    for count, edge_left, edge_right in zip(n, bins[:-1], bins[1:]):
        center = (edge_left + edge_right) / 2
        if count > 0:
            plt.text(center, count + max(n)*0.01, int(count), ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.show()
