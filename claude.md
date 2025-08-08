iagnóstico do erro (NameError: tab6 is not defined)
Onde o erro ocorre
Linha 1205 de interface_web.py: with tab6:
Por que ocorre
A variável tab6 é criada apenas dentro do bloco
O bloco da nova aba “Story Points” (linhas 1205-1416) está fora desse if.
Quando a aplicação inicia, ainda não existe nenhum df carregado, portanto o bloco if não é executado e tab6 não é criado. Ao chegar na linha 1205 o Python não encontra a variável e dispara o NameError.
Correção imediata
Mova todo o bloco “Story Points” (ou qualquer outro que use tabX) para dentro do mesmo if onde os tabs são criados; ou
Mantenha-o fora, mas antes de usar verifique se tab6 existe:
Alternativamente combine as duas coisas: coloque o conteúdo dentro de uma função e só invoque a função quando df estiver presente.
O que melhorar na aplicação (análise geral)
Organização do código
Arquivo único com ~1400 linhas dificulta manutenção.
Separe em módulos: ui_sidebar.py, ui_tabs.py, charts.py, data_service.py, etc.
Coloque
Coloque funções reutilizáveis (ex.: criação de métricas, gráficos) em utilitários isolados.
Considere usar o recurso “multipage” do Streamlit (streamlit run app.py -- …) ou st.pages para dividir cada aba em um arquivo .py.
Carregamento e cache dos dados
Use @st.cache_data (ou @st.experimental_memo em versões antigas) em sprint_service.analisar_sprint para não chamar a API do Jira a cada st.rerun().
Valide as colunas imediatamente após o carregamento; se faltar alguma coluna crítica, mostre aviso claro em vez de deixar estourar exceção na exibição.
Verificação de pré-condições
Antes de cada aba que usa certos campos (datas, story points, etc.), adicione if com mensagem amigável quando o dado não estiver presente.
No caso das abas criadas dinamicamente (st.tabs), mantenha todo o conteúdo dentro do mesmo bloco onde as variáveis do tab existem.
Código defensivo e legibilidade
Substitua cadeias longas de if status in [...] por dicionários/sets ou por expressões regulares.
Construa funções como calc_dias_para_resolucao(df) e build_status_color_map() para evitar código duplicado.
UX
Evite mostrar tabelas muito grandes por padrão – forneça paginação (st.dataframe com argumento height ou use AgGrid).
Para campos de filtro, use placeholder e valores iniciais inteligentes (ex.: data mínima/máxima da sprint).
Performance de renderização
Alguns gráficos Plotly com muitas barras podem ficar lentos; avalie usar px.histogram agregado ou fig.update_xaxes(type='category') para melhorar.
Se o DataFrame for grande, considere carregar apenas colunas necessárias para cada aba.
Logging e debug
Substitua prints (st.write) por logging com níveis; deixe um toggle “Modo debug” na sidebar para exibir se necessário.
Resumo
O erro é causado por uso de tab6 fora do escopo em que foi criado; mova ou proteja o bloco.
Refatore o arquivo em módulos, aplique cache nos acessos ao Jira, valide dados antes de usar e cuide de UX/performance para uma aplicação mais robusta e escalável.