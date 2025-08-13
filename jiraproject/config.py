"""
Configurações centralizadas da aplicação Dashboard Jira.
"""

from typing import List
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class DashboardConfig:
    """Configurações centralizadas do dashboard."""
    
    # === CONFIGURAÇÕES DE INTERFACE ===
    
    # Projetos sugeridos na interface
    PROJETOS_SUGERIDOS: List[str] = [
        "SMD",
        "[DIGITAL] Sites / Marketing", 
        "[DIGITAL] CredCesta CORE",
        "VAC",
        "smd",
        "vac"
    ]
    
    # Story Points candidatos para análise
    STORY_POINTS_CANDIDATOS: List[int] = [3, 5, 8, 13, 21]
    
    # === CONFIGURAÇÕES DE CACHE ===
    
    # TTL do cache em segundos
    CACHE_TTL_SPRINTS: int = int(os.getenv("CACHE_TTL_SPRINTS", "300"))  # 5 minutos
    CACHE_TTL_PROJETOS: int = int(os.getenv("CACHE_TTL_PROJETOS", "600"))  # 10 minutos
    
    # === CONFIGURAÇÕES DO JIRA ===
    
    # Custom fields comuns do Jira para Story Points
    JIRA_STORY_POINTS_FIELDS: List[str] = [
        "customfield_10016",
        "customfield_10026", 
        "customfield_10031",
        "customfield_10010"
    ]
    
    # Status que indicam trabalho em progresso
    STATUS_EM_PROGRESSO: List[str] = [
        'Em Progresso',
        'In Progress', 
        'Fazendo',
        'Desenvolvimento',
        'Code Review',
        'QA',
        'Testing'
    ]
    
    # === CONFIGURAÇÕES DE PERFORMANCE ===
    
    # Limite de itens por consulta Jira
    JIRA_MAX_RESULTS: int = int(os.getenv("JIRA_MAX_RESULTS", "1000"))
    
    # Timeout para requisições HTTP (segundos)
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))
    
    # === CONFIGURAÇÕES DE SEGURANÇA ===
    
    # Tempo de sessão em minutos
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    
    # Rate limiting - máximo de requisições por minuto
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
    # === CONFIGURAÇÕES DE LOG ===
    
    # Nível de log
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Formato de data
    DATE_FORMAT: str = "%d/%m/%Y"
    DATETIME_FORMAT: str = "%d/%m/%Y %H:%M:%S"


# Instância global de configuração
config = DashboardConfig()