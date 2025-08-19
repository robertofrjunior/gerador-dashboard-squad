"""
Sistema de cache inteligente.
"""

from .smart_cache import (
    SmartCache, 
    smart_cache_data, 
    CacheManager, 
    cache_manager,
    show_cache_controls,
    adaptive_cache_config
)

__all__ = [
    'SmartCache', 
    'smart_cache_data', 
    'CacheManager', 
    'cache_manager',
    'show_cache_controls',
    'adaptive_cache_config'
]