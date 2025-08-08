# 🌐 Interface Web - Dashboard Sprint Jira

Uma interface web completa e amigável para análise de sprints do Jira, desenvolvida com Streamlit.

## 🚀 Como Executar

### 1. Ativar o ambiente virtual
```bash
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows
```

### 2. Executar a interface
```bash
streamlit run interface_web.py
```

### 3. Acessar no navegador
A interface será aberta automaticamente em: `http://localhost:8501`

### 4. Alternativa com Make (recomendado)

```bash
make venv   # cria .venv e instala dependências
make test   # executa pytest com PYTHONPATH=.
```
Depois rode a interface normalmente: `streamlit run interface_web.py`.

## 🎯 Funcionalidades da Interface

### ⚙️ **Configurações (Sidebar)**
- **Input de Projeto/Squad**: Campo de texto para nome do projeto
- **Input de Sprint ID**: Campo numérico para ID da sprint
- **Botão de Busca**: Carrega os dados do Jira
- **Histórico**: Mostra informações da última análise
- **Botão Limpar**: Remove dados carregados

### 📊 **Métricas Principais**
- **Total de Issues**: Número total de itens na sprint
- **Itens Ágeis**: História, Débito Técnico e Spike
- **Story Points**: Total de pontos planejados
- **Concluídos**: Itens com status de conclusão
- **Responsáveis**: Número de pessoas na sprint

### 📋 **Abas Disponíveis**

#### 1. **📊 Visão Geral**
- Gráficos de pizza para distribuição por tipo e status
- Tabelas resumo com percentuais
- Pivot table completa (Tipos × Responsáveis)

#### 2. **🎯 Análise por Responsável**
- **Visão Geral**: Resumo de todos os responsáveis
- **Análise Individual**: Métricas específicas por pessoa
- **Gráficos Personalizados**: Para cada responsável
- **Lista de Itens**: Detalhamento por pessoa

#### 3. **🔍 Filtros Avançados**
- **Filtros Múltiplos**: Status, Tipo de Item, Responsável
- **Métricas Filtradas**: Estatísticas dos dados filtrados
- **Visualizações Especiais**: Sunburst e Treemap
- **Pivot Table Filtrada**: Com aplicação dos filtros

#### 4. **📋 Dados Detalhados**
- **Controle de Colunas**: Selecionar quais mostrar
- **Ordenação**: Por qualquer coluna
- **Estatísticas**: Métricas dos dados exibidos
- **Export CSV**: Download dos dados

#### 5. **📈 Gráficos Interativos**
- **Heatmap**: Distribuição visual intensiva
- **Barras Empilhadas**: Composição por responsável
- **Scatter Plot**: Story Points dispersos
- **Análise de Correlação**: Relações entre variáveis

## 🎨 **Recursos Visuais**

### **Gráficos Interativos (Plotly)**
- Zoom, pan e hover interativo
- Legendas clicáveis
- Múltiplas escalas de cores
- Responsivo para diferentes telas

### **Componentes Streamlit**
- Métricas com deltas coloridos
- Multiselect para filtros
- Progress bars e spinners
- Cards informativos
- Botões de download

### **Estilo Customizado**
- CSS personalizado para melhor aparência
- Cards com bordas coloridas
- Seções destacadas
- Layout responsivo

## 🔧 **Exemplos de Uso**

### **Análise Básica**
1. Digite "smd" no campo Projeto
2. Digite "4450" no campo Sprint ID
3. Clique em "Buscar Dados da Sprint"
4. Explore as abas disponíveis

### **Análise Filtrada**
1. Vá para a aba "Filtros Avançados"
2. Selecione status específicos (ex: "Concluído", "Done")
3. Selecione tipos específicos (ex: "História", "Bug")
4. Visualize os resultados filtrados

### **Análise Individual**
1. Vá para a aba "Análise por Responsável"
2. Selecione uma pessoa específica
3. Visualize métricas individuais
4. Analise a distribuição de trabalho

### **Export de Dados**
1. Vá para a aba "Dados Detalhados"
2. Configure as colunas desejadas
3. Defina ordenação
4. Clique em "Download dos Dados (CSV)"

## 📱 **Compatibilidade**

### **Navegadores Suportados**
- ✅ Chrome/Chromium
- ✅ Firefox  
- ✅ Safari
- ✅ Edge

### **Dispositivos**
- 💻 Desktop (recomendado)
- 📱 Tablet (funcional)
- 📱 Mobile (limitado)

## 🔒 **Segurança**

- Dados processados localmente
- Sem armazenamento permanente
- Conexão direta com Jira via API
- Credenciais no arquivo .env

## ⚡ **Performance**

### **Otimizações**
- Cache de dados no session_state
- Lazy loading de gráficos
- Processamento otimizado de pandas
- Renderização condicional

### **Limites Recomendados**
- Máximo 1000 issues por sprint
- Máximo 20 responsáveis diferentes
- Tempo de resposta: < 10 segundos

## 🐛 **Troubleshooting**

### **Problemas Comuns**

#### **"Nenhum dado encontrado"**
- Verifique se o projeto existe no Jira
- Confirme se o ID da sprint está correto
- Verifique as credenciais no .env

#### **"Erro ao buscar dados"**
- Verifique conexão com internet
- Confirme se o token Jira está válido
- Verifique se há issues na sprint

#### **Interface não carrega**
- Confirme se o Streamlit está instalado
- Verifique se todas as dependências estão OK
- Tente reiniciar o servidor

### **Comandos Úteis**
```bash
# Verificar se Streamlit está instalado
streamlit --version

# Limpar cache do Streamlit
streamlit cache clear

# Executar em porta específica
streamlit run interface_web.py --server.port 8502

# Executar sem abrir navegador
streamlit run interface_web.py --server.headless true
```

## 🧱 Arquitetura (resumo)

- `interface_web.py`: app Streamlit. Não fala JQL diretamente; usa o service.
- `jiraproject/services/jira.py`: fachada para o Jira.
  - Valida projeto, busca sprints e histórico.
  - Constrói JQL com builders e executa via cliente genérico.
- `jiraproject/utils/jql.py`: builders de JQL padronizadas.
  - `build_validate_project_jql(proj)`: valida projeto.
  - `build_historico_jql(proj, inicio, fim)`: histórico concluídos com SP.
  - `build_sprint_jql_variants(proj, sprint_id)`: variantes para Sprint.
- `jiraproject/utils/jira_fields.py`: listas de campos padronizados para JQL.
  - `default_fields()`, `sprint_fields()`, `historico_fields()`.
- `jiraproject/utils_*`: utilitários (datas, normalização, Arrow, constantes).
- `credcesta/jira_client.py`: cliente HTTP baixo nível (REST Jira).
  - Expõe `executar_jql(jql, ...)` usado pela fachada.

Fluxo típico (Histórico):
`interface_web.py` → `services/jira.buscar_issues_por_periodo` → `utils/jql.build_historico_jql` → `jira_client.executar_jql` → DataFrame/Exibição.

## 🤝 **Suporte**

Para problemas ou sugestões:
1. Verifique este README primeiro
2. Consulte a documentação do Streamlit
3. Analise os logs de erro no terminal
4. Teste com dados menores primeiro

---

**💡 Dica**: Para melhor experiência, use em tela cheia no navegador desktop!