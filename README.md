# Análise de Sprints do Jira

Este projeto fornece uma ferramenta de linha de comando para analisar sprints do Jira, gerando métricas e visualizações sobre o desempenho da equipe.

## Configuração

1.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure as variáveis de ambiente:**
    Crie um arquivo `.env` na raiz do projeto, baseado no `.env.sample`, e preencha com suas credenciais do Jira:
    ```
    JIRA_URL=https://bancomaster.atlassian.net
    JIRA_EMAIL=seu-email@exemplo.com
    JIRA_API_TOKEN=seu-token-de-api
    ```

## Como Usar

Execute a análise através da linha de comando, fornecendo o nome do projeto e o ID da sprint.

```bash
python -m credcesta.cli analisar --projeto "Meu Projeto" --sprint 1234
```

Ou, se instalado via pacote:

```bash
sprint-analyzer --projeto "Meu Projeto" --sprint 1234
```

### Argumentos

-   `--projeto` ou `-p`: (Obrigatório) Nome do projeto no Jira.
-   `--sprint` ou `-s`: (Obrigatório) ID da Sprint para análise.

### Saída

A ferramenta gera:
- **Métricas no console**: Distribuição por tipo de item, story points e responsáveis
- **Gráficos de visualização**: Exibidos automaticamente
- **Arquivo CSV**: Salvo no diretório atual com dados detalhados da sprint

### Nomes de Arquivo

O arquivo CSV é salvo com nome baseado no projeto e sprint. Caracteres especiais são automaticamente sanitizados:

- Colchetes `[]` são removidos
- Barras `/` e espaços são substituídos por `_`
- Apenas caracteres alfanuméricos, pontos, hífens e underscores são mantidos

**Exemplo:**
- Projeto: `[DIGITAL] Sites / Marketing`
- Sprint: `4450`
- Arquivo gerado: `DIGITAL_Sites_Marketing_4450_analysis.csv`

## Instalação via Pacote (Recomendado para Usuários)

Se você não precisa modificar o código, a forma mais fácil de instalar é usando o pacote de distribuição.

1.  **Construa o pacote** (se ainda não tiver sido feito):
    ```bash
    pip install build
    python -m build
    ```

2.  **Instale o arquivo Wheel gerado:**
    O comando acima criará um arquivo no diretório `dist/`. Instale-o com:
    ```bash
    pip install dist/credcesta_sprint_analyzer-0.1.0-py3-none-any.whl
    ```

3.  **Configure as credenciais** criando um arquivo `.env` (veja a seção de configuração acima).

4.  **Execute a ferramenta:**
    Após a instalação, o comando `sprint-analyzer` estará disponível no seu terminal:
    ```bash
    sprint-analyzer --projeto "Meu Projeto" --sprint 1234
    ```

## Checklist Concluído

- [x] Estrutura do projeto modularizada (`credcesta/`)
- [x] Ambiente virtual criado e dependências instaladas (`requirements.txt`)
- [x] Arquivo `.env` configurado com credenciais do Jira
- [x] CLI (`python -m credcesta`) funcionando e gerando CSV + gráficos
- [x] Notebook legado movido para `notebooks/` (somente referência)
- [x] README documentado com instalação e uso
- [x] **Correções robustas aplicadas:**
  - [x] Sanitização de nomes de arquivo (remove caracteres especiais)
  - [x] Criação automática de diretórios para CSV
  - [x] Tratamento melhorado de campo responsável não encontrado
  - [x] Suite de testes abrangente (18 testes passando)

## Próximos Passos

| Prioridade | Atividade | Status |
|-----------|-----------|--------|
| Alta | ~~Escrever casos de teste automatizados (`pytest`, `requests-mock`)~~ | ✅ |
| Alta | Configurar pipeline de CI (GitHub Actions) para lint (`flake8`) + testes | ☐ |
| Média | Publicar pacote interno (PyPI privado ou artefato Docker) | ☐ |
| Média | Adicionar badge de cobertura de testes | ☐ |
| Baixa | Gerar documentação automática (Sphinx) | ☐ |
| Baixa | Implementar cache das respostas do Jira (Redis ou Parquet local) | ☐ |

Execute os itens em ordem de prioridade para evoluir a aplicação.
