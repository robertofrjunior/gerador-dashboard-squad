"""
Modelos de validação usando Pydantic.
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
import re


class JiraCredentials(BaseModel):
    """Modelo para credenciais do Jira."""
    
    jira_url: HttpUrl = Field(..., description="URL do servidor Jira")
    email: str = Field(..., min_length=5, max_length=100, description="Email do usuário")
    token: str = Field(..., min_length=20, max_length=200, description="Token de API")
    
    @validator('email')
    def validate_email(cls, v):
        """Valida formato do email."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Email deve ter formato válido')
        return v.lower()
    
    @validator('jira_url')
    def validate_jira_url(cls, v):
        """Valida URL do Jira."""
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL deve começar com http:// ou https://')
        
        # Verificar se parece com URL do Jira
        jira_patterns = [
            r'.*\.atlassian\.net.*',
            r'.*jira.*',
            r'.*\:8080.*'
        ]
        
        if not any(re.search(pattern, url_str, re.IGNORECASE) for pattern in jira_patterns):
            # Warning, mas não erro - permitir URLs customizadas
            pass
            
        return v


class SprintFilter(BaseModel):
    """Modelo para filtros de sprint."""
    
    projeto: str = Field(..., min_length=1, max_length=50, description="Nome do projeto")
    sprint_ids: List[int] = Field(..., min_items=1, max_items=20, description="IDs das sprints")
    include_sub_tasks: bool = Field(default=True, description="Incluir sub-tarefas")
    only_agile_items: bool = Field(default=True, description="Apenas itens ágeis")
    
    @validator('projeto')
    def validate_projeto(cls, v):
        """Valida nome do projeto."""
        # Remover espaços extras
        v = v.strip()
        
        # Verificar caracteres válidos
        if not re.match(r'^[a-zA-Z0-9\s\[\]\-_\.]+$', v):
            raise ValueError('Projeto contém caracteres inválidos')
        
        return v
    
    @validator('sprint_ids')
    def validate_sprint_ids(cls, v):
        """Valida IDs das sprints."""
        # Verificar se todos são positivos
        if any(sid <= 0 for sid in v):
            raise ValueError('IDs de sprint devem ser positivos')
        
        # Remover duplicatas mantendo ordem
        seen = set()
        unique_ids = []
        for sid in v:
            if sid not in seen:
                seen.add(sid)
                unique_ids.append(sid)
        
        return unique_ids


class DateRangeFilter(BaseModel):
    """Modelo para filtros de data."""
    
    start_date: Optional[date] = Field(None, description="Data de início")
    end_date: Optional[date] = Field(None, description="Data de fim")
    date_field: str = Field(default="created", description="Campo de data para filtrar")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Valida intervalo de datas."""
        if 'start_date' in values and values['start_date'] and v:
            if v < values['start_date']:
                raise ValueError('Data de fim deve ser posterior à data de início')
            
            # Verificar se intervalo não é muito grande (1 ano)
            if (v - values['start_date']).days > 365:
                raise ValueError('Intervalo não pode ser maior que 1 ano')
        
        return v
    
    @validator('date_field')
    def validate_date_field(cls, v):
        """Valida campo de data."""
        valid_fields = ['created', 'updated', 'resolved', 'due']
        if v not in valid_fields:
            raise ValueError(f'Campo de data deve ser um de: {", ".join(valid_fields)}')
        return v


class AnalysisConfig(BaseModel):
    """Modelo para configuração de análise."""
    
    include_weekends: bool = Field(default=False, description="Incluir fins de semana nos cálculos")
    business_hours_only: bool = Field(default=False, description="Apenas horário comercial")
    timezone: str = Field(default="America/Sao_Paulo", description="Fuso horário")
    exclude_status: List[str] = Field(default=[], description="Status a excluir")
    story_points_field: Optional[str] = Field(None, description="Campo customizado para Story Points")
    
    @validator('timezone')
    def validate_timezone(cls, v):
        """Valida fuso horário."""
        # Lista simplificada de fusos válidos
        valid_timezones = [
            'America/Sao_Paulo', 'America/New_York', 'Europe/London',
            'UTC', 'America/Chicago', 'Europe/Amsterdam'
        ]
        
        if v not in valid_timezones:
            raise ValueError(f'Fuso horário deve ser um de: {", ".join(valid_timezones)}')
        
        return v


class DashboardRequest(BaseModel):
    """Modelo para requisição completa do dashboard."""
    
    credentials: JiraCredentials
    sprint_filter: SprintFilter
    date_filter: Optional[DateRangeFilter] = None
    analysis_config: Optional[AnalysisConfig] = None
    dashboard_type: str = Field(default="scrum", description="Tipo de dashboard")
    
    @validator('dashboard_type')
    def validate_dashboard_type(cls, v):
        """Valida tipo de dashboard."""
        valid_types = ['scrum', 'kanban', 'custom']
        if v not in valid_types:
            raise ValueError(f'Tipo de dashboard deve ser um de: {", ".join(valid_types)}')
        return v


class ApiResponse(BaseModel):
    """Modelo para resposta da API."""
    
    success: bool = Field(..., description="Se a operação foi bem-sucedida")
    data: Optional[Any] = Field(None, description="Dados retornados")
    error: Optional[str] = Field(None, description="Mensagem de erro")
    warnings: List[str] = Field(default=[], description="Avisos")
    metadata: Dict[str, Any] = Field(default={}, description="Metadados adicionais")
    
    @validator('error')
    def validate_error_message(cls, v, values):
        """Valida mensagem de erro."""
        if not values.get('success') and not v:
            raise ValueError('Mensagem de erro é obrigatória quando success=False')
        return v


class CacheConfig(BaseModel):
    """Modelo para configuração de cache."""
    
    ttl_seconds: int = Field(default=300, ge=60, le=3600, description="TTL em segundos")
    max_size: int = Field(default=100, ge=10, le=1000, description="Tamanho máximo do cache")
    per_user: bool = Field(default=True, description="Cache específico por usuário")
    compress: bool = Field(default=False, description="Comprimir dados do cache")


class SecurityConfig(BaseModel):
    """Modelo para configuração de segurança."""
    
    session_timeout_minutes: int = Field(default=30, ge=5, le=480, description="Timeout da sessão")
    max_requests_per_minute: int = Field(default=100, ge=10, le=1000, description="Rate limit")
    require_https: bool = Field(default=True, description="Exigir HTTPS")
    log_sensitive_data: bool = Field(default=False, description="Logar dados sensíveis")


def validate_input(data: Dict[str, Any], model_class: BaseModel) -> BaseModel:
    """
    Valida entrada usando modelo Pydantic.
    
    Args:
        data: Dados para validar
        model_class: Classe do modelo Pydantic
        
    Returns:
        Instância validada do modelo
        
    Raises:
        ValidationError: Se dados são inválidos
    """
    try:
        return model_class(**data)
    except Exception as e:
        # Reformatar erro para ser mais amigável
        error_msg = str(e)
        if "validation error" in error_msg.lower():
            lines = error_msg.split('\n')
            simplified = []
            for line in lines:
                if 'field required' in line:
                    field = line.split()[0] if line.split() else 'campo'
                    simplified.append(f"Campo '{field}' é obrigatório")
                elif 'ensure this value' in line:
                    simplified.append(line.strip())
            
            if simplified:
                error_msg = '; '.join(simplified)
        
        raise ValueError(f"Dados inválidos: {error_msg}")


def sanitize_for_api(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitiza dados sensíveis antes de enviar para API.
    
    Args:
        data: Dados originais
        
    Returns:
        Dados sanitizados
    """
    sanitized = data.copy()
    
    # Campos sensíveis para mascarar
    sensitive_fields = ['token', 'password', 'api_key', 'secret']
    
    def mask_recursive(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                key: '[MASKED]' if key.lower() in sensitive_fields else mask_recursive(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [mask_recursive(item) for item in obj]
        else:
            return obj
    
    return mask_recursive(sanitized)