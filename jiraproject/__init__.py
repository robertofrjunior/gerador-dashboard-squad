"""Pacote utilitário para integração Jira e utilidades da aplicação."""

# Reexport utilidades para compatibilidade com testes antigos
from .utils import log  # noqa: F401
try:
    # mover util de compatibilidade
    from .credcesta.utils import sanitize_filename  # type: ignore
except Exception:
    # fallback: expor uma implementação básica
    import re
    def sanitize_filename(filename: str) -> str:  # type: ignore
        if not filename:
            return filename
        sanitized = filename.replace('[', '').replace(']', '')
        sanitized = sanitized.replace('/', '_').replace(' ', '_')
        sanitized = re.sub(r'[^A-Za-z0-9._-]', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.strip('_')
