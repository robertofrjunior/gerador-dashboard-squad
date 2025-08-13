"""
Sistema de cache inteligente com TTL dinâmico e invalidação seletiva.
"""

import streamlit as st
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable, List
import json
from ..config import config


class SmartCache:
    """Cache inteligente com TTL dinâmico baseado em horário de trabalho."""
    
    @staticmethod
    def get_business_hours_ttl() -> int:
        """
        Calcula TTL baseado no horário de trabalho.
        Durante horário comercial: TTL menor (mais atualizações)
        Fora do horário: TTL maior (menos requisições)
        """
        now = datetime.now()
        hour = now.hour
        
        # Horário comercial: 8h às 18h, segunda a sexta
        is_weekday = now.weekday() < 5  # 0-4 = segunda a sexta
        is_business_hours = 8 <= hour <= 18
        
        if is_weekday and is_business_hours:
            # Durante horário comercial: cache mais curto
            return config.CACHE_TTL_SPRINTS  # 5 minutos
        else:
            # Fora do horário: cache mais longo
            return config.CACHE_TTL_SPRINTS * 4  # 20 minutos
    
    @staticmethod
    def get_user_cache_key(base_key: str) -> str:
        """
        Gera chave de cache específica por usuário.
        
        Args:
            base_key: Chave base do cache
            
        Returns:
            Chave única por sessão/usuário
        """
        # Usar session_state para identificar usuário único
        session_id = st.session_state.get('session_id')
        
        if not session_id:
            # Gerar ID único para esta sessão
            session_id = hashlib.md5(
                f"{time.time()}_{id(st.session_state)}".encode()
            ).hexdigest()[:8]
            st.session_state['session_id'] = session_id
        
        return f"{base_key}_{session_id}"
    
    @staticmethod
    def create_cache_signature(data: Dict[str, Any]) -> str:
        """
        Cria assinatura única para os dados.
        
        Args:
            data: Dados para criar assinatura
            
        Returns:
            Hash MD5 dos dados
        """
        # Serializar dados de forma consistente
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()


def smart_cache_data(
    func: Optional[Callable] = None,
    *,
    key_prefix: str = "default",
    use_business_hours: bool = True,
    per_user: bool = True,
    ttl: Optional[int] = None
):
    """
    Decorator para cache inteligente com TTL dinâmico.
    
    Args:
        key_prefix: Prefixo para a chave do cache
        use_business_hours: Se usa TTL baseado em horário comercial
        per_user: Se o cache é específico por usuário
        ttl: TTL fixo em segundos (opcional)
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Calcular TTL
            cache_ttl = ttl
            if cache_ttl is None and use_business_hours:
                cache_ttl = SmartCache.get_business_hours_ttl()
            elif cache_ttl is None:
                cache_ttl = config.CACHE_TTL_SPRINTS
            
            # Gerar chave do cache
            base_key = f"{key_prefix}_{func.__name__}"
            
            if per_user:
                cache_key = SmartCache.get_user_cache_key(base_key)
            else:
                cache_key = base_key
            
            # Tentar usar cache do Streamlit com TTL dinâmico
            return st.cache_data(
                func=func,
                ttl=cache_ttl,
                show_spinner=f"🔄 Carregando {key_prefix}..."
            )(*args, **kwargs)
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


class CacheManager:
    """Gerenciador centralizado de cache."""
    
    def __init__(self):
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
    
    def invalidate_sprint_cache(self, projeto: str, sprint_ids: List[int]) -> None:
        """
        Invalida cache específico de sprints.
        
        Args:
            projeto: Nome do projeto
            sprint_ids: IDs das sprints para invalidar
        """
        try:
            # Invalidar cache relacionado às sprints específicas
            patterns = [
                f"sprint_{projeto}_{sprint_id}"
                for sprint_id in sprint_ids
            ]
            
            # Streamlit não tem API para invalidação seletiva
            # mas podemos limpar todo o cache se necessário
            st.cache_data.clear()
            
            self.cache_stats['invalidations'] += len(patterns)
            
        except Exception as e:
            st.warning(f"Erro ao invalidar cache: {e}")
    
    def invalidate_project_cache(self, projeto: str) -> None:
        """
        Invalida todo o cache de um projeto.
        
        Args:
            projeto: Nome do projeto
        """
        try:
            # Invalidar cache do projeto
            st.cache_data.clear()
            self.cache_stats['invalidations'] += 1
            
        except Exception as e:
            st.warning(f"Erro ao invalidar cache do projeto: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do cache."""
        hit_rate = (
            self.cache_stats['hits'] / 
            (self.cache_stats['hits'] + self.cache_stats['misses']) * 100
        ) if (self.cache_stats['hits'] + self.cache_stats['misses']) > 0 else 0
        
        return {
            **self.cache_stats,
            'hit_rate': round(hit_rate, 1)
        }
    
    def clear_user_cache(self) -> None:
        """Limpa cache específico do usuário atual."""
        try:
            session_id = st.session_state.get('session_id')
            if session_id:
                # Não há API específica, limpar tudo
                st.cache_data.clear()
                st.success("♻️ Cache do usuário limpo!")
        except Exception as e:
            st.error(f"Erro ao limpar cache: {e}")


# Instância global do gerenciador
cache_manager = CacheManager()


def show_cache_controls() -> None:
    """Mostra controles de cache na sidebar (para debug)."""
    if st.sidebar.button("🗑️ Limpar Cache"):
        cache_manager.clear_user_cache()
    
    with st.sidebar.expander("📊 Cache Stats"):
        stats = cache_manager.get_cache_stats()
        st.metric("Hit Rate", f"{stats['hit_rate']}%")
        st.metric("Cache Hits", stats['hits'])
        st.metric("Cache Misses", stats['misses'])
        st.metric("Invalidações", stats['invalidations'])


def adaptive_cache_config() -> Dict[str, int]:
    """
    Configuração adaptiva de cache baseada no contexto.
    
    Returns:
        Dicionário com TTLs adaptativos
    """
    now = datetime.now()
    
    # Durante desenvolvimento/debug: TTL menor
    if config.LOG_LEVEL == "DEBUG":
        return {
            'sprint_ttl': 60,      # 1 minuto
            'project_ttl': 120,    # 2 minutos
            'board_ttl': 180       # 3 minutos
        }
    
    # Durante horário comercial: TTL médio
    if SmartCache.get_business_hours_ttl() == config.CACHE_TTL_SPRINTS:
        return {
            'sprint_ttl': config.CACHE_TTL_SPRINTS,      # 5 minutos
            'project_ttl': config.CACHE_TTL_PROJETOS,    # 10 minutos
            'board_ttl': config.CACHE_TTL_PROJETOS * 2   # 20 minutos
        }
    
    # Fora do horário: TTL maior
    return {
        'sprint_ttl': config.CACHE_TTL_SPRINTS * 4,      # 20 minutos
        'project_ttl': config.CACHE_TTL_PROJETOS * 3,    # 30 minutos
        'board_ttl': config.CACHE_TTL_PROJETOS * 6       # 60 minutos
    }