"""
Utilitários gerais para o projeto CredCesta.
"""
import re


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza um nome de arquivo removendo caracteres problemáticos.
    
    Remove ou substitui caracteres que podem causar problemas em sistemas de arquivos:
    - Remove colchetes []
    - Substitui barras / por underscore _
    - Substitui espaços por underscore _
    - Mantém apenas caracteres alfanuméricos, pontos, underscores e hífens
    
    Args:
        filename (str): Nome do arquivo original
        
    Returns:
        str: Nome do arquivo sanitizado
        
    Examples:
        >>> sanitize_filename("[DIGITAL] Sites / Marketing_4450_analysis.csv")
        'DIGITAL_Sites_Marketing_4450_analysis.csv'
        >>> sanitize_filename("Test File (Copy).txt")
        'Test_File_Copy.txt'
    """
    if not filename:
        return filename
    
    # Remove colchetes
    sanitized = filename.replace('[', '').replace(']', '')
    
    # Substitui barras e espaços por underscore
    sanitized = sanitized.replace('/', '_').replace(' ', '_')
    
    # Remove caracteres especiais, mantendo apenas: letras, números, pontos, underscores e hífens
    sanitized = re.sub(r'[^A-Za-z0-9._-]', '_', sanitized)
    
    # Remove underscores múltiplos consecutivos
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove underscores no início e fim
    sanitized = sanitized.strip('_')
    
    return sanitized