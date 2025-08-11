# Refatoração da Aplicação Jira Dashboard

Data: 2025-08-08

## Objetivo
Refatorar a aplicação Streamlit para análise de sprints do Jira, focando em modularização, eliminação de duplicações, padronização de logs/UI, centralização de JQL e garantia de estabilidade (no-break).

## Checklist do que já foi refatorado (Concluído)
- [x] Modularização de utilidades
  - [x] `jiraproject/utils_constants.py` (constantes globais)
  - [x] `jiraproject/utils_normalize.py` (normalização/canônicos)
  - [x] `jiraproject/utils_dates.py` (cálculo de dias, datas seguras)
  - [x] `jiraproject/utils_arrow.py` (compatibilidade PyArrow/Streamlit)
- [x] Camada de serviço e centralização de JQL
  - [x] `jiraproject/services/jira.py` (fachada de serviços)
  - [x] `jiraproject/utils/jql.py` (builders de JQL)
  - [x] `jiraproject/utils/jira_fields.py` (listas de fields padronizadas)
  - [x] `jiraproject/jira_client.py`: função genérica `executar_jql` e uso dos builders em caminhos críticos
- [x] Padronização de logs
  - [x] `jiraproject/utils/log.py` com `info/ok/warn/error` e substituição de `print`
- [x] Encapsulamento de UI
  - [x] `jiraproject/utils/ui.py` com `tipo_icon`, `status_color`, `build_column_config`, `metric`, `pct_delta`, `bar`, `pie`, `status_bar_figure`
  - [x] Substituição de chamadas diretas a `st.metric`, `px.bar`, `px.pie` e dicionários de coluna por helpers
- [x] Aba “Story Points”
  - [x] Filtro por tipos (História, Débito Técnico, Spike) e SP > 0
  - [x] Modo histórico por período (JQL revisada, campos `created/resolved`)
  - [x] Cálculo de “Dias para Resolução” e tabela média por SP
- [x] Seleção de sprints
  - [x] Lista a sprint ativa + 5 sprints fechadas mais recentes
  - [x] Selectbox único no lugar de múltiplos botões
  - [x] Limpeza de cache e session_state ao trocar projeto/squad
- [x] Compatibilidade Arrow/PyArrow e tipos
  - [x] `make_display_copy` com `numeric_cols` opcional e substituição segura de NaN por `—` para exibição
  - [x] Separação entre dados para cálculo e dados para display
- [x] Testes e automação
  - [x] `tests/test_utils.py` cobrindo utils e builders
  - [x] Ajustes em `tests/test_cli.py` e `tests/test_jira_client.py`
  - [x] `Makefile` com `venv` e `test`
  - [x] `requirements.txt` atualizado (incl. `pytest-mock`, `requests-mock`)
- [x] Ajustes gerais
  - [x] Correções de `IndentationError` e `TypeError`
  - [x] Troca de namespace “jiraproject” para “jiraproject” conforme combinado
  - [x] `README_INTERFACE.md` com instruções e arquitetura

## Pendências e Próximos Passos
- [ ] Padronizar títulos/legendas/tema dos gráficos via helpers
  - [ ] Criar helper de layout (ex.: `apply_chart_layout(fig, title, legend, yaxis_title, ...)`)
  - [ ] Aplicar `update_layout`/`update_traces` padrão em `bar/pie/status_bar_figure`
- [ ] Expandir `build_column_config`
  - [ ] Incluir mais colunas comuns (links, datas, numéricos, status, tipo)
  - [ ] Centralizar máscaras/formatos (dias, porcentagens, Story Points)
<<<<<<< HEAD
- [ ] Migrar JQLs restantes para builders
  - [ ] Mapear todos os pontos ainda usando JQL literal ou `jira_client` direto
  - [ ] Encaminhar tudo via `services/jira.py` + builders em `utils/jql.py`
=======
- [x] Migrar JQLs restantes para builders
  - [x] Mapear todos os pontos ainda usando JQL literal ou `jira_client` direto
  - [x] Encaminhar tudo via `services/jira.py` + builders em `utils/jql.py`
>>>>>>> origin/main
- [ ] Consolidar cálculos e nomes de colunas
  - [ ] Usar `calc_dias` em todos os pontos de cálculo de “Dias para Resolução”
  - [ ] Padronizar o nome “Dias para Resolução” (evitar variações)
- [ ] Encapsular grupos de métricas/cartões
  - [ ] Criar helpers para painéis de métricas repetidos (ex.: resumo de tempo, resumo por responsável)
- [ ] Melhorar mensagens de erro/UX
  - [ ] Usar `utils/log.py` e mensagens de UI consistentes (prefixos, ícones, tons)
- [ ] Aumentar cobertura de testes
  - [ ] Testes de `services/jira.py` com mocks
  - [ ] Testes de `utils/jql.py` (bordas e variações)
- [ ] Documentação
  - [ ] Adicionar arquitetura resumida e fluxo de dados no `README_INTERFACE.md`
  - [ ] Adicionar notas de desempenho/cache (chaves por projeto/board)
- [ ] (Opcional) CI
  - [ ] Configurar workflow simples (lint + testes) no GitHub Actions

## Plano de Execução Imediato (Fase 3)
1. Criar helper de layout para gráficos e aplicar em `bar`, `pie`, `status_bar_figure` (padronização visual)
2. Expandir `build_column_config` para novas colunas mapeadas, mantendo mapeamento em um único lugar
3. Migrar JQLs restantes para `services/jira` + `utils/jql` (eliminação de literais)
4. Revisar `interface_web.py` para remover duplicações restantes e unificar nomes de colunas
5. Adicionar testes para serviços e builders (casos borda)

## Como Validar
- Testes automatizados:
  - `make test`
- Executar app:
  - `streamlit run interface_web.py`

## Histórico
- 2025-08-08: Consolidação das fases 1 e 2, correções de indentação/Arrow, padronização de UI/helper, testes verdes.
